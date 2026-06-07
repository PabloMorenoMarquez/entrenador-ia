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


# ─────────────────────────────────────────
# CONVERSACIONES (Fase 7)
# ─────────────────────────────────────────

def guardar_conversacion_sb(rol: str, contenido: str) -> None:
    sb = get_client()
    uid = get_user_id()
    sb.table("conversaciones").insert({
        "user_id": uid,
        "rol": rol,
        "contenido": contenido,
    }).execute()


def leer_conversaciones_sb(limite: int = 10) -> list[dict]:
    sb = get_client()
    uid = get_user_id()
    result = (
        sb.table("conversaciones")
        .select("rol, contenido, timestamp")
        .eq("user_id", uid)
        .order("timestamp", desc=True)
        .limit(limite)
        .execute()
    )
    rows = list(reversed(result.data or []))
    return [{"rol": r["rol"], "contenido": r["contenido"]} for r in rows]


# ─────────────────────────────────────────
# MACROS OBJETIVO (Fase 7)
# ─────────────────────────────────────────

def guardar_macros_objetivo_sb(periodo: str, macros: dict) -> None:
    sb = get_client()
    uid = get_user_id()
    sb.table("macros_objetivo").update({"activa": False}).eq("user_id", uid).eq("periodo", periodo).eq("activa", True).execute()
    sb.table("macros_objetivo").insert({
        "user_id": uid,
        "periodo": periodo,
        "kcal": macros.get("kcal"),
        "proteinas_g": macros.get("proteinas_g"),
        "carbos_g": macros.get("carbos_g"),
        "grasas_g": macros.get("grasas_g"),
        "notas": macros.get("notas", ""),
        "activa": True,
    }).execute()


def leer_macros_objetivo_sb(periodo: str = "dia") -> Optional[dict]:
    sb = get_client()
    uid = get_user_id()
    result = (
        sb.table("macros_objetivo")
        .select("*")
        .eq("user_id", uid)
        .eq("periodo", periodo)
        .eq("activa", True)
        .order("fecha_calculo", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    row = result.data[0]
    fc = row.get("fecha_calculo") or ""
    return {
        "kcal": row.get("kcal") or 0,
        "proteinas_g": row.get("proteinas_g") or 0,
        "carbos_g": row.get("carbos_g") or 0,
        "grasas_g": row.get("grasas_g") or 0,
        "notas": row.get("notas") or "",
        "fecha_calculo": fc[:10] if fc else "",
    }


# ─────────────────────────────────────────
# REGISTRO COMIDAS (Fase 7)
# ─────────────────────────────────────────

def guardar_comidas_sb(datos: dict) -> int:
    sb = get_client()
    uid = get_user_id()
    from datetime import datetime as _dt
    ahora = _dt.now()
    comida = datos.get("comida") or {}
    tipo_comida = comida.get("tipo_comida") or ""
    notas_comida = comida.get("notas") or ""
    alimentos = datos.get("alimentos") or []
    rows = [{
        "user_id": uid,
        "fecha": ahora.strftime("%Y-%m-%d"),
        "hora": ahora.strftime("%H:%M"),
        "tipo_comida": tipo_comida,
        "alimento": al.get("alimento") or "",
        "cantidad_g_ml": al.get("cantidad_g_ml") or None,
        "calorias": al.get("calorias") or None,
        "proteinas_g": al.get("proteinas_g") or None,
        "carbos_g": al.get("carbos_g") or None,
        "grasas_g": al.get("grasas_g") or None,
        "fibra_g": al.get("fibra_g") or None,
        "notas": al.get("notas") or notas_comida,
    } for al in alimentos]
    if rows:
        sb.table("registro_comidas").insert(rows).execute()
    return len(rows)


def leer_comidas_fecha_sb(fecha: str) -> list[dict]:
    sb = get_client()
    uid = get_user_id()
    result = (
        sb.table("registro_comidas")
        .select("*")
        .eq("user_id", uid)
        .eq("fecha", fecha)
        .order("hora")
        .execute()
    )
    return result.data or []


def leer_comidas_rango_sb(desde: str, hasta: str) -> list[dict]:
    sb = get_client()
    uid = get_user_id()
    result = (
        sb.table("registro_comidas")
        .select("*")
        .eq("user_id", uid)
        .gte("fecha", desde)
        .lte("fecha", hasta)
        .order("fecha")
        .execute()
    )
    return result.data or []


# ─────────────────────────────────────────
# HISTORIAL ENTRENAMIENTOS (Fase 7)
# ─────────────────────────────────────────

def _to_num_repo(val) -> float:
    try:
        return float(str(val).replace(",", "."))
    except (ValueError, TypeError):
        return 0.0


def guardar_entreno_sb(datos: dict, sesion_id: str) -> None:
    sb = get_client()
    uid = get_user_id()
    from datetime import datetime as _dt
    ahora = _dt.now()
    sesion = datos.get("sesion") or {}
    sb.table("historial_entrenamientos").upsert({
        "user_id": uid,
        "sesion_id": sesion_id,
        "fecha": ahora.strftime("%Y-%m-%d"),
        "hora_inicio": ahora.strftime("%H:%M"),
        "duracion_min": sesion.get("duracion_min") or None,
        "tipo_sesion": sesion.get("tipo_sesion") or None,
        "grupo_muscular_principal": sesion.get("grupo_muscular_principal") or None,
        "nivel_energia": sesion.get("nivel_energia") or None,
        "nivel_esfuerzo": sesion.get("nivel_esfuerzo") or None,
        "notas_sesion": sesion.get("notas") or None,
    }, on_conflict="user_id,sesion_id").execute()
    ejercicios = datos.get("ejercicios") or []
    if ejercicios:
        rows = [{
            "user_id": uid,
            "sesion_id": sesion_id,
            "fecha": ahora.strftime("%Y-%m-%d"),
            "orden": i + 1,
            "ejercicio": ej.get("ejercicio") or "",
            "grupo_muscular": ej.get("grupo_muscular") or None,
            "series": ej.get("series") or None,
            "reps_objetivo": str(ej.get("reps_objetivo") or ""),
            "reps_realizadas": str(ej.get("reps_realizadas") or ""),
            "peso_kg": ej.get("peso_kg") or None,
            "tipo_peso": ej.get("tipo_peso") or None,
            "descanso_seg": ej.get("descanso_seg") or None,
            "rir": ej.get("rir") or None,
            "notas": ej.get("notas") or None,
        } for i, ej in enumerate(ejercicios)]
        sb.table("ejercicios_detalle").insert(rows).execute()


def leer_rutina_sb() -> Optional[dict]:
    sb = get_client()
    uid = get_user_id()
    r = (
        sb.table("historial_entrenamientos")
        .select("sesion_id, fecha")
        .eq("user_id", uid)
        .order("fecha", desc=True)
        .limit(1)
        .execute()
    )
    if not r.data:
        return None
    last = r.data[0]
    sesion_id, fecha = last["sesion_id"], last["fecha"]
    ej_r = (
        sb.table("ejercicios_detalle")
        .select("*")
        .eq("user_id", uid)
        .eq("sesion_id", sesion_id)
        .order("orden")
        .execute()
    )
    ejercicios = [{
        "orden": ej.get("orden") or 0,
        "ejercicio": ej.get("ejercicio") or "",
        "grupo_muscular": ej.get("grupo_muscular") or "",
        "series": ej.get("series") or 0,
        "reps_objetivo": ej.get("reps_objetivo") or "",
        "reps_realizadas": ej.get("reps_realizadas") or "",
        "peso_kg": ej.get("peso_kg") or 0,
        "tipo_peso": ej.get("tipo_peso") or "",
        "descanso_seg": ej.get("descanso_seg") or 0,
        "rir": ej.get("rir") or 0,
        "notas": ej.get("notas") or "",
    } for ej in (ej_r.data or [])]
    return {"sesion_id": sesion_id, "fecha": fecha, "ejercicios": ejercicios}


# ─────────────────────────────────────────
# PLAN DE RUTINA SEMANAL (objetivo vs realidad)
# ─────────────────────────────────────────

def guardar_rutina_plan_dia(dia_semana: str, ejercicios: list[dict]) -> None:
    sb = get_client()
    uid = get_user_id()
    sb.table("rutina_plan").delete().eq("user_id", uid).eq("dia_semana", dia_semana).execute()
    if not ejercicios:
        return
    rows = [{
        "user_id": uid,
        "dia_semana": dia_semana,
        "orden": i + 1,
        "ejercicio": ej.get("ejercicio") or "",
        "grupo_muscular": ej.get("grupo_muscular") or None,
        "series_objetivo": ej.get("series_objetivo") or None,
        "reps_objetivo": ej.get("reps_objetivo") or None,
        "notas": ej.get("notas") or None,
    } for i, ej in enumerate(ejercicios)]
    sb.table("rutina_plan").insert(rows).execute()


def leer_rutina_plan_sb() -> dict:
    sb = get_client()
    uid = get_user_id()
    r = (
        sb.table("rutina_plan").select("*")
        .eq("user_id", uid).order("dia_semana").order("orden")
        .execute()
    )
    dias: dict = {}
    for fila in (r.data or []):
        dia = fila.get("dia_semana") or ""
        dias.setdefault(dia, []).append({
            "orden": fila.get("orden") or 0,
            "ejercicio": fila.get("ejercicio") or "",
            "grupo_muscular": fila.get("grupo_muscular") or "",
            "series_objetivo": fila.get("series_objetivo"),
            "reps_objetivo": fila.get("reps_objetivo") or "",
            "notas": fila.get("notas") or "",
        })
    return dias


def leer_ultimas_ejecuciones_sb(nombres: list) -> dict:
    """Última ejecución registrada de cada ejercicio (por nombre, case-insensitive).
    Permite comparar el objetivo del plan con lo realmente hecho la última vez."""
    if not nombres:
        return {}
    sb = get_client()
    uid = get_user_id()
    r = (
        sb.table("ejercicios_detalle")
        .select("ejercicio, fecha, series, reps_realizadas, peso_kg, rir")
        .eq("user_id", uid)
        .order("fecha", desc=True)
        .limit(400)
        .execute()
    )
    objetivo_lower = {n.strip().lower() for n in nombres}
    resultado: dict = {}
    for fila in (r.data or []):
        clave = (fila.get("ejercicio") or "").strip().lower()
        if clave in objetivo_lower and clave not in resultado:
            resultado[clave] = {
                "fecha": fila.get("fecha") or "",
                "series": fila.get("series") or 0,
                "reps_realizadas": fila.get("reps_realizadas") or "",
                "peso_kg": fila.get("peso_kg") or 0,
                "rir": fila.get("rir"),
            }
    return resultado


def leer_historial_sb(limite: int = 30) -> dict:
    sb = get_client()
    uid = get_user_id()
    s_r = (
        sb.table("historial_entrenamientos")
        .select("*")
        .eq("user_id", uid)
        .order("fecha", desc=True)
        .limit(limite)
        .execute()
    )
    sesiones = s_r.data or []
    if not sesiones:
        return {"sesiones": []}
    sids = [s["sesion_id"] for s in sesiones]
    ej_r = (
        sb.table("ejercicios_detalle")
        .select("sesion_id, series, reps_realizadas, reps_objetivo, peso_kg")
        .eq("user_id", uid)
        .in_("sesion_id", sids)
        .execute()
    )
    vol: dict[str, float] = {}
    for ej in (ej_r.data or []):
        sid = ej.get("sesion_id", "")
        s = ej.get("series") or 0
        reps = _to_num_repo(ej.get("reps_realizadas") or ej.get("reps_objetivo"))
        peso = ej.get("peso_kg") or 0
        vol[sid] = vol.get(sid, 0) + s * reps * peso
    return {"sesiones": [{
        "sesion_id": s["sesion_id"],
        "fecha": s.get("fecha", ""),
        "hora_inicio": str(s.get("hora_inicio") or ""),
        "duracion_min": s.get("duracion_min") or 0,
        "tipo_sesion": s.get("tipo_sesion") or "",
        "grupo_muscular_principal": s.get("grupo_muscular_principal") or "",
        "nivel_energia": s.get("nivel_energia") or 0,
        "nivel_esfuerzo": s.get("nivel_esfuerzo") or 0,
        "notas": s.get("notas_sesion") or "",
        "volumen_total_kg": round(vol.get(s["sesion_id"], 0), 1),
    } for s in sesiones]}


# ─────────────────────────────────────────
# CONFIGURACIÓN ESTÁTICA (Fase 7)
# ─────────────────────────────────────────

def leer_configuracion_sb(hoja: str) -> Optional[tuple]:
    """Retorna (contenido_texto, datos_json) o None si no existe."""
    sb = get_client()
    uid = get_user_id()
    result = (
        sb.table("configuracion")
        .select("contenido_texto, datos_json")
        .eq("user_id", uid)
        .eq("hoja", hoja)
        .execute()
    )
    if not result.data:
        return None
    row = result.data[0]
    return row.get("contenido_texto", ""), row.get("datos_json") or {}


def guardar_configuracion_sb(hoja: str, contenido_texto: str = "", datos_json: dict = None) -> None:
    sb = get_client()
    uid = get_user_id()
    sb.table("configuracion").upsert({
        "user_id": uid,
        "hoja": hoja,
        "contenido_texto": contenido_texto,
        "datos_json": datos_json or {},
        "updated_at": date.today().isoformat(),
    }, on_conflict="user_id,hoja").execute()
