"""
Capa de acceso a datos Supabase para tablas de recuperación (Fase 1) y memoria semántica (Fase 2).
Todas las funciones son síncronas (llamadas desde asyncio.to_thread donde sea necesario).
"""

import os
from datetime import date, timedelta
from typing import Optional
from db.supabase_client import get_client, get_user_id


# ─────────────────────────────────────────
# EMBEDDINGS (compartido con rag/buscar_contexto.py)
# ─────────────────────────────────────────

def _generar_embedding(texto: str) -> list[float]:
    """Genera embedding con text-embedding-3-small (mismo modelo que el RAG)."""
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
    response = client.embeddings.create(model="text-embedding-3-small", input=texto)
    return response.data[0].embedding


# ─────────────────────────────────────────
# MEMORIA SEMÁNTICA (Fase 2)
# ─────────────────────────────────────────

# Días de expiración por prioridad (igual que Sheets decay)
_DIAS_EXPIRY = {1: 7, 2: 30, 3: 90}   # prioridad 4-5 → nunca expira


def guardar_memoria_semantica(entrada: dict) -> bool:
    """
    Guarda entrada de memoria en Supabase con dedup semántica real.
    Si similitud > 0.92 con una existente → refuerza prioridad, no duplica.
    Retorna True si guardó nueva entrada, False si era duplicado.
    """
    sb = get_client()
    uid = get_user_id()

    contenido = (entrada.get("contenido") or "").strip()
    if not contenido:
        return False

    embedding = _generar_embedding(contenido)

    # Dedup semántica: buscar top-3 entradas similares
    try:
        result = sb.rpc("buscar_memoria", {
            "query_embedding": embedding,
            "p_user_id": uid,
            "match_count": 3,
            "min_prioridad": 1,
        }).execute()
        for entry in (result.data or []):
            if entry.get("similarity", 0) > 0.92:
                # Duplicado semántico: reforzar prioridad
                nueva_prio = max(entry.get("prioridad", 3), entrada.get("prioridad", 3))
                sb.table("memory").update({"prioridad": nueva_prio}).eq("id", entry["id"]).execute()
                print(f"[memoria] Dedup: reforzado '{contenido[:50]}...' (sim={entry['similarity']:.2f})")
                return False
    except Exception as e:
        print(f"[memoria] Dedup check fallida (continuando): {e}")

    # Calcular expiración
    prioridad = entrada.get("prioridad", 3)
    dias = _DIAS_EXPIRY.get(prioridad)
    fecha_expiracion = (date.today() + timedelta(days=dias)).isoformat() if dias else None

    payload = {
        "user_id": uid,
        "tipo": entrada.get("tipo", "general"),
        "contenido": contenido,
        "prioridad": prioridad,
        "embedding": embedding,
        "activa": True,
        "fecha_expiracion": fecha_expiracion,
    }
    sb.table("memory").insert(payload).execute()
    print(f"[memoria] Guardado: '{contenido[:60]}...' (p{prioridad})")
    return True


def buscar_memoria_semantica(query_texto: str, match_count: int = 8) -> str:
    """
    Busca memoria relevante a la pregunta actual por similitud semántica + prioridad.
    Retorna bloque de texto formateado para inyectar al prompt.
    """
    sb = get_client()
    uid = get_user_id()

    embedding = _generar_embedding(query_texto)

    result = sb.rpc("buscar_memoria", {
        "query_embedding": embedding,
        "p_user_id": uid,
        "match_count": match_count,
        "min_prioridad": 1,
    }).execute()

    entries = result.data or []
    if not entries:
        return ""

    lineas = []
    for e in entries:
        tipo = e.get("tipo") or "general"
        contenido = e.get("contenido", "")
        prioridad = e.get("prioridad", 3)
        lineas.append(f"[{tipo}, p{prioridad}] {contenido}")

    return "\n".join(lineas)


def decay_memoria_supabase() -> int:
    """
    Marca como inactivas las entradas expiradas. Una sola query vs iterar filas.
    Retorna número de entradas expiradas.
    """
    sb = get_client()
    uid = get_user_id()
    hoy = date.today().isoformat()

    result = (
        sb.table("memory")
        .update({"activa": False})
        .eq("user_id", uid)
        .eq("activa", True)
        .not_.is_("fecha_expiracion", "null")
        .lt("fecha_expiracion", hoy)
        .execute()
    )
    count = len(result.data or [])
    if count:
        print(f"[decay_memoria] {count} entradas expiradas en Supabase")
    return count


# ─────────────────────────────────────────
# BIOMÉTRICOS
# ─────────────────────────────────────────

def guardar_biometricos(datos: dict) -> dict:
    """
    Upsert de biométricos. datos puede venir del form manual o del Watch.
    Requiere al menos 'fecha'. 'fuente' por defecto 'manual'.
    """
    sb = get_client()
    uid = get_user_id()
    payload = {
        "user_id": uid,
        "fecha": datos.get("fecha", date.today().isoformat()),
        "fuente": datos.get("fuente", "manual"),
        **{k: v for k, v in datos.items() if k not in ("fecha", "fuente", "user_id")},
    }
    result = (
        sb.table("biometricos")
        .upsert(payload, on_conflict="user_id,fecha,fuente")
        .execute()
    )
    return result.data[0] if result.data else {}


def leer_biometricos_hoy() -> Optional[dict]:
    sb = get_client()
    uid = get_user_id()
    hoy = date.today().isoformat()
    result = (
        sb.table("biometricos")
        .select("*")
        .eq("user_id", uid)
        .eq("fecha", hoy)
        .order("fuente")  # watch antes que manual si los dos existen
        .execute()
    )
    # Merge manual + watch: watch tiene prioridad para campos del sensor
    rows = result.data or []
    if not rows:
        return None
    merged = {}
    for row in rows:
        for k, v in row.items():
            if v is not None:
                merged[k] = v
    return merged


def leer_biometricos_recientes(dias: int = 7) -> list[dict]:
    sb = get_client()
    uid = get_user_id()
    desde = (date.today() - timedelta(days=dias)).isoformat()
    result = (
        sb.table("biometricos")
        .select("*")
        .eq("user_id", uid)
        .gte("fecha", desde)
        .order("fecha", desc=True)
        .execute()
    )
    return result.data or []


# ─────────────────────────────────────────
# CHECK-IN MATUTINO
# ─────────────────────────────────────────

def guardar_checkin(datos: dict) -> dict:
    sb = get_client()
    uid = get_user_id()
    payload = {
        "user_id": uid,
        "fecha": datos.get("fecha", date.today().isoformat()),
        **{k: v for k, v in datos.items() if k not in ("fecha", "user_id")},
    }
    result = (
        sb.table("checkin_matutino")
        .upsert(payload, on_conflict="user_id,fecha")
        .execute()
    )
    return result.data[0] if result.data else {}


def leer_checkin_hoy() -> Optional[dict]:
    sb = get_client()
    uid = get_user_id()
    hoy = date.today().isoformat()
    result = (
        sb.table("checkin_matutino")
        .select("*")
        .eq("user_id", uid)
        .eq("fecha", hoy)
        .execute()
    )
    return result.data[0] if result.data else None


def leer_checkin_recientes(dias: int = 7) -> list[dict]:
    sb = get_client()
    uid = get_user_id()
    desde = (date.today() - timedelta(days=dias)).isoformat()
    result = (
        sb.table("checkin_matutino")
        .select("*")
        .eq("user_id", uid)
        .gte("fecha", desde)
        .order("fecha", desc=True)
        .execute()
    )
    return result.data or []


# ─────────────────────────────────────────
# MEDIDAS CORPORALES
# ─────────────────────────────────────────

def guardar_medidas(datos: dict) -> dict:
    sb = get_client()
    uid = get_user_id()
    payload = {
        "user_id": uid,
        "fecha": datos.get("fecha", date.today().isoformat()),
        **{k: v for k, v in datos.items() if k not in ("fecha", "user_id")},
    }
    result = (
        sb.table("body_measurements")
        .upsert(payload, on_conflict="user_id,fecha")
        .execute()
    )
    return result.data[0] if result.data else {}


def leer_medidas_recientes(limite: int = 10) -> list[dict]:
    sb = get_client()
    uid = get_user_id()
    result = (
        sb.table("body_measurements")
        .select("*")
        .eq("user_id", uid)
        .order("fecha", desc=True)
        .limit(limite)
        .execute()
    )
    return result.data or []


# ─────────────────────────────────────────
# HIDRATACIÓN
# ─────────────────────────────────────────

def guardar_hidratacion(litros: float, fecha: Optional[str] = None) -> dict:
    sb = get_client()
    uid = get_user_id()
    payload = {
        "user_id": uid,
        "fecha": fecha or date.today().isoformat(),
        "litros": litros,
    }
    result = (
        sb.table("hidratacion")
        .upsert(payload, on_conflict="user_id,fecha")
        .execute()
    )
    return result.data[0] if result.data else {}


def leer_hidratacion_hoy() -> Optional[float]:
    sb = get_client()
    uid = get_user_id()
    hoy = date.today().isoformat()
    result = (
        sb.table("hidratacion")
        .select("litros")
        .eq("user_id", uid)
        .eq("fecha", hoy)
        .execute()
    )
    return result.data[0]["litros"] if result.data else None


# ─────────────────────────────────────────
# DOLOR / LESIONES
# ─────────────────────────────────────────

def registrar_dolor(zona: str, intensidad: int, notas: str = "", fecha: Optional[str] = None) -> dict:
    sb = get_client()
    uid = get_user_id()
    payload = {
        "user_id": uid,
        "fecha": fecha or date.today().isoformat(),
        "zona": zona,
        "intensidad": intensidad,
        "activo": intensidad > 0,
        "notas": notas,
    }
    result = sb.table("dolor_lesion").insert(payload).execute()
    return result.data[0] if result.data else {}


def leer_dolores_activos() -> list[dict]:
    sb = get_client()
    uid = get_user_id()
    result = (
        sb.table("dolor_lesion")
        .select("zona, intensidad, notas, fecha")
        .eq("user_id", uid)
        .eq("activo", True)
        .order("fecha", desc=True)
        .execute()
    )
    return result.data or []


def leer_dolores_hoy() -> list[dict]:
    sb = get_client()
    uid = get_user_id()
    hoy = date.today().isoformat()
    result = (
        sb.table("dolor_lesion")
        .select("zona, intensidad, notas")
        .eq("user_id", uid)
        .eq("fecha", hoy)
        .execute()
    )
    return result.data or []


# ─────────────────────────────────────────
# PLAN NUTRICIONAL CON TIMING (Fase 5)
# ─────────────────────────────────────────

def guardar_plan_nutricional(
    tomas: list,
    hora_entreno: Optional[str] = None,
    notas: str = "",
    fecha: Optional[str] = None,
) -> dict:
    """Upsert del plan nutricional del día."""
    sb = get_client()
    uid = get_user_id()
    payload = {
        "user_id": uid,
        "fecha": fecha or date.today().isoformat(),
        "hora_entreno": hora_entreno,
        "tomas": tomas,
        "notas": notas,
        "generado_por": "llm",
    }
    result = (
        sb.table("plan_nutricional")
        .upsert(payload, on_conflict="user_id,fecha")
        .execute()
    )
    return result.data[0] if result.data else {}


def leer_plan_nutricional_hoy() -> Optional[dict]:
    """Retorna el plan nutricional de hoy o None si no existe."""
    sb = get_client()
    uid = get_user_id()
    hoy = date.today().isoformat()
    result = (
        sb.table("plan_nutricional")
        .select("*")
        .eq("user_id", uid)
        .eq("fecha", hoy)
        .execute()
    )
    return result.data[0] if result.data else None


def leer_cronotipo() -> Optional[str]:
    """Retorna el cronotipo del usuario (matutino/vespertino/intermedio)."""
    sb = get_client()
    uid = get_user_id()
    result = (
        sb.table("cronotipo")
        .select("tipo")
        .eq("user_id", uid)
        .limit(1)
        .execute()
    )
    return result.data[0]["tipo"] if result.data else None
