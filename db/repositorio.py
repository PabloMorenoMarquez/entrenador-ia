"""
Capa de acceso a datos Supabase para las tablas de recuperación (Fase 1).
Todas las funciones son síncronas (llamadas desde asyncio.to_thread donde sea necesario).
"""

from datetime import date, timedelta
from typing import Optional
from db.supabase_client import get_client, get_user_id


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
