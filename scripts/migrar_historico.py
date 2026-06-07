"""
Backfill histórico Sheets → Supabase (paso final de Fase 7, antes de apagar Sheets).

El dual-write (commit fea9cf2) solo cubre escrituras nuevas hacia delante, y el
lazy-populate de lectura solo copia lo que entra en la ventana leída ("últimas 20
sesiones", "comidas de hoy/semana", etc). Filas más antiguas que esa ventana nunca
se leen → nunca se copian → se quedan huérfanas en Sheets para siempre.

Este script recorre TODA la sheet de cada tabla histórica y vuelca a Supabase lo
que falte. Idempotente: comprueba qué existe ya en Supabase antes de insertar, así
que se puede ejecutar varias veces sin duplicar filas.

Uso (desde la raíz del proyecto):
    python scripts/migrar_historico.py                                # las 4 tablas
    python scripts/migrar_historico.py conversaciones registro_comidas
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

from memory.conectar_sheets import conectar, _get_spreadsheet, NOMBRE_HOJAS
from db.supabase_client import get_client, get_user_id


def _filas_crudas(nombre_hoja: str) -> list[list[str]]:
    """Todas las filas de la sheet, sin la cabecera, leídas por posición de columna
    (mismo orden que usan las funciones _guardar_*_sync de conectar_sheets.py)."""
    cliente = conectar()
    hoja = _get_spreadsheet(cliente).worksheet(NOMBRE_HOJAS[nombre_hoja])
    filas = hoja.get_all_values()
    return filas[1:] if len(filas) > 1 else []


def _v(fila, i, default=""):
    return fila[i].strip() if len(fila) > i and fila[i].strip() else default


def _num(fila, i):
    val = _v(fila, i)
    if not val:
        return None
    try:
        return float(val.replace(",", "."))
    except ValueError:
        return None


# ── conversaciones — columnas: ID, TIMESTAMP, ROL, CONTENIDO ──

def migrar_conversaciones() -> None:
    sb = get_client()
    uid = get_user_id()
    filas = _filas_crudas("conversaciones")

    existentes = (
        sb.table("conversaciones").select("contenido, timestamp")
        .eq("user_id", uid).execute().data or []
    )
    vistos = {(e["contenido"], (e.get("timestamp") or "")[:19]) for e in existentes}

    rows = []
    for fila in filas:
        timestamp, rol, contenido = _v(fila, 1), _v(fila, 2, "user"), _v(fila, 3)
        if not contenido or (contenido, timestamp[:19]) in vistos:
            continue
        rows.append({"user_id": uid, "rol": rol, "contenido": contenido, "timestamp": timestamp or None})

    if rows:
        sb.table("conversaciones").insert(rows).execute()
    print(f"[conversaciones] {len(rows)} filas nuevas migradas (de {len(filas)} en Sheets)")


# ── historial_entrenamientos — columnas: sesion_id, fecha, hora, "", duracion_min,
#    tipo_sesion, grupo_muscular_principal, "", nivel_energia, nivel_esfuerzo, "", notas
# ── ejercicios_detalle — columnas: sesion_id, fecha, orden, ejercicio, grupo_muscular,
#    series, reps_objetivo, reps_realizadas, peso_kg, tipo_peso, descanso_seg, rir, notas

def migrar_entrenamientos() -> None:
    sb = get_client()
    uid = get_user_id()
    sesiones = _filas_crudas("historial_entrenamientos")
    ejercicios = _filas_crudas("ejercicios_detalle")

    existentes = (
        sb.table("historial_entrenamientos").select("sesion_id")
        .eq("user_id", uid).execute().data or []
    )
    sids_existentes = {e["sesion_id"] for e in existentes}

    nuevas = []
    for fila in sesiones:
        sid = _v(fila, 0)
        if not sid or sid in sids_existentes:
            continue
        nuevas.append({
            "user_id": uid,
            "sesion_id": sid,
            "fecha": _v(fila, 1) or None,
            "hora_inicio": _v(fila, 2) or None,
            "duracion_min": _num(fila, 4),
            "tipo_sesion": _v(fila, 5) or None,
            "grupo_muscular_principal": _v(fila, 6) or None,
            "nivel_energia": _num(fila, 8),
            "nivel_esfuerzo": _num(fila, 9),
            "notas_sesion": _v(fila, 11) or None,
        })
    if nuevas:
        sb.table("historial_entrenamientos").upsert(nuevas, on_conflict="user_id,sesion_id").execute()

    # Detalle de ejercicios solo para sesiones recién insertadas — las que ya
    # existían en Supabase ya trajeron su detalle al guardarse (guardar_entreno_sb).
    sids_nuevas = {n["sesion_id"] for n in nuevas}
    rows_ej = []
    for fila in ejercicios:
        sid = _v(fila, 0)
        if sid not in sids_nuevas:
            continue
        rows_ej.append({
            "user_id": uid,
            "sesion_id": sid,
            "fecha": _v(fila, 1) or None,
            "orden": int(_num(fila, 2) or 0),
            "ejercicio": _v(fila, 3),
            "grupo_muscular": _v(fila, 4) or None,
            "series": _num(fila, 5),
            "reps_objetivo": _v(fila, 6),
            "reps_realizadas": _v(fila, 7),
            "peso_kg": _num(fila, 8),
            "tipo_peso": _v(fila, 9) or None,
            "descanso_seg": _num(fila, 10),
            "rir": _num(fila, 11),
            "notas": _v(fila, 12) or None,
        })
    if rows_ej:
        sb.table("ejercicios_detalle").insert(rows_ej).execute()

    print(f"[entrenamientos] {len(nuevas)} sesiones + {len(rows_ej)} ejercicios migrados "
          f"(de {len(sesiones)} sesiones en Sheets)")


# ── registro_comidas — columnas: fecha, hora, tipo_comida, alimento, cantidad_g_ml,
#    calorias, proteinas_g, carbos_g, grasas_g, fibra_g, notas

def migrar_comidas() -> None:
    sb = get_client()
    uid = get_user_id()
    filas = _filas_crudas("registro_comidas")

    existentes = (
        sb.table("registro_comidas").select("fecha, hora, alimento")
        .eq("user_id", uid).execute().data or []
    )
    vistos = {(e["fecha"], e.get("hora"), e["alimento"]) for e in existentes}

    rows = []
    for fila in filas:
        fecha, hora, alimento = _v(fila, 0), _v(fila, 1), _v(fila, 3)
        if not fecha or not alimento or (fecha, hora, alimento) in vistos:
            continue
        rows.append({
            "user_id": uid,
            "fecha": fecha,
            "hora": hora or None,
            "tipo_comida": _v(fila, 2) or None,
            "alimento": alimento,
            "cantidad_g_ml": _num(fila, 4),
            "calorias": _num(fila, 5),
            "proteinas_g": _num(fila, 6),
            "carbos_g": _num(fila, 7),
            "grasas_g": _num(fila, 8),
            "fibra_g": _num(fila, 9),
            "notas": _v(fila, 10) or None,
        })
    if rows:
        sb.table("registro_comidas").insert(rows).execute()
    print(f"[comidas] {len(rows)} filas nuevas migradas (de {len(filas)} en Sheets)")


MIGRACIONES = {
    "conversaciones": migrar_conversaciones,
    "historial_entrenamientos": migrar_entrenamientos,
    "registro_comidas": migrar_comidas,
}


if __name__ == "__main__":
    objetivo = sys.argv[1:] or list(MIGRACIONES.keys())
    for nombre in objetivo:
        fn = MIGRACIONES.get(nombre)
        if not fn:
            print(f"[migrar_historico] Tabla desconocida: '{nombre}'. Opciones: {list(MIGRACIONES)}")
            continue
        print(f"--- Migrando {nombre} ---")
        try:
            fn()
        except Exception as e:
            print(f"[migrar_historico] Error en {nombre}: {e}")
