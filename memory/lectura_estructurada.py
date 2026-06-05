"""
Funciones de lectura estructurada para los endpoints REST de la SPA.
Reusa la capa de conexión de conectar_sheets.py.
"""

import asyncio
from datetime import date, datetime, timedelta

from memory.conectar_sheets import (
    conectar,
    _get_spreadsheet,
    _leer_hoja_sync,
    _to_num,
    NOMBRE_HOJAS,
    leer_macros_objetivo_activos,
    guardar_macros_objetivo,
)


# ---- perfil_usuario (key-value vertical) ----

def _leer_perfil_sync() -> dict:
    """
    perfil_usuario es key-value vertical: col A = campo, col B = valor.
    get_all_values() devuelve lista de listas; la primera fila puede ser cabecera.
    Devuelve dict {campo_lower: valor}.
    """
    cliente = conectar()
    hoja = _get_spreadsheet(cliente).worksheet(NOMBRE_HOJAS["perfil_usuario"])
    filas = hoja.get_all_values()
    resultado = {}
    for fila in filas:
        if len(fila) >= 2 and fila[0] and fila[0].lower() not in ("campo", "etiqueta", "clave", "key"):
            resultado[fila[0].lower().strip()] = fila[1].strip() if fila[1] else ""
    return resultado


def _guardar_perfil_sync(campos: dict) -> None:
    """
    Actualiza campos en perfil_usuario.
    Si la fila existe (col A coincide) → update col B.
    Si no existe → append_row([campo, valor]).
    """
    import gspread.utils as gu
    cliente = conectar()
    hoja = _get_spreadsheet(cliente).worksheet(NOMBRE_HOJAS["perfil_usuario"])
    filas = hoja.get_all_values()

    # índice: campo_lower → número de fila (1-based)
    mapa_filas = {}
    for i, fila in enumerate(filas, start=1):
        if fila and fila[0]:
            mapa_filas[fila[0].lower().strip()] = i

    updates = []
    nuevos = []
    for campo, valor in campos.items():
        campo_norm = campo.lower().strip()
        if campo_norm in mapa_filas:
            row_num = mapa_filas[campo_norm]
            cell = gu.rowcol_to_a1(row_num, 2)  # col B
            updates.append({"range": cell, "values": [[str(valor)]]})
        else:
            nuevos.append([campo, str(valor)])

    if updates:
        hoja.batch_update(updates)
    for fila_nueva in nuevos:
        hoja.append_row(fila_nueva)


# ---- rutina (última sesión de ejercicios_detalle) ----

def _leer_rutina_sync() -> dict:
    """
    Devuelve los ejercicios de la sesión más reciente en ejercicios_detalle.
    """
    cliente = conectar()
    filas = _leer_hoja_sync(cliente, NOMBRE_HOJAS["ejercicios_detalle"])
    if not filas:
        return {"sesion_id": None, "fecha": None, "ejercicios": []}

    # Encontrar el SESION_ID más reciente
    ultimo_sesion_id = filas[-1].get("SESION_ID", "")
    for fila in reversed(filas):
        sid = fila.get("SESION_ID", "")
        if sid:
            ultimo_sesion_id = sid
            break

    ejercicios_sesion = [f for f in filas if f.get("SESION_ID") == ultimo_sesion_id]
    fecha = ejercicios_sesion[0].get("FECHA", "") if ejercicios_sesion else ""

    ejercicios = []
    for ej in sorted(ejercicios_sesion, key=lambda x: _to_num(x.get("ORDEN", 0))):
        ejercicios.append({
            "orden": _to_num(ej.get("ORDEN")),
            "ejercicio": ej.get("EJERCICIO", ""),
            "grupo_muscular": ej.get("GRUPO_MUSCULAR", ""),
            "series": _to_num(ej.get("SERIES")),
            "reps_objetivo": ej.get("REPS_OBJETIVO", ""),
            "reps_realizadas": ej.get("REPS_REALIZADAS", ""),
            "peso_kg": _to_num(ej.get("PESO_KG")),
            "tipo_peso": ej.get("TIPO_PESO", ""),
            "descanso_seg": _to_num(ej.get("DESCANSO_SEG")),
            "rir": _to_num(ej.get("RIR")),
            "notas": ej.get("NOTAS_EJERCICIO", ""),
        })

    return {"sesion_id": ultimo_sesion_id, "fecha": fecha, "ejercicios": ejercicios}


# ---- nutrición ----

def _sumar_macros(filas: list[dict]) -> dict:
    total = {"kcal": 0, "proteinas_g": 0, "carbos_g": 0, "grasas_g": 0}
    for f in filas:
        total["kcal"] += _to_num(f.get("CALORIAS"))
        total["proteinas_g"] += _to_num(f.get("PROTEINAS_G"))
        total["carbos_g"] += _to_num(f.get("CARBOS_G"))
        total["grasas_g"] += _to_num(f.get("GRASAS_G"))
    return total


_MACRO_KEYS = ("kcal", "proteinas_g", "carbos_g", "grasas_g")

def _calcular_delta(objetivo: dict, consumido: dict) -> dict:
    return {k: round(consumido[k] - objetivo[k], 1) for k in _MACRO_KEYS}


def _leer_comidas_sync() -> list[dict]:
    cliente = conectar()
    return _leer_hoja_sync(cliente, NOMBRE_HOJAS["registro_comidas"])


def _leer_nutricion_hoy_sync(objetivo: dict) -> dict:
    hoy = date.today().isoformat()
    todas = _leer_comidas_sync()
    de_hoy = [f for f in todas if f.get("FECHA", "") == hoy]
    consumido = _sumar_macros(de_hoy)
    comidas = [
        {
            "hora": f.get("HORA", ""),
            "tipo_comida": f.get("TIPO_COMIDA", ""),
            "alimento": f.get("ALIMENTO", ""),
            "cantidad_g_ml": _to_num(f.get("CANTIDAD_G_ML")),
            "calorias": _to_num(f.get("CALORIAS")),
            "proteinas_g": _to_num(f.get("PROTEINAS_G")),
            "carbos_g": _to_num(f.get("CARBOS_G")),
            "grasas_g": _to_num(f.get("GRASAS_G")),
            "fibra_g": _to_num(f.get("FIBRA_G")),
            "notas": f.get("NOTAS", ""),
        }
        for f in de_hoy
    ]
    return {
        "fecha": hoy,
        "objetivo": objetivo,
        "consumido": consumido,
        "delta": _calcular_delta(objetivo, consumido),
        "comidas": comidas,
    }


def _leer_nutricion_semana_sync(objetivo: dict) -> dict:
    hoy = date.today()
    fechas_semana = [(hoy - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
    todas = _leer_comidas_sync()

    dias = []
    for fecha in fechas_semana:
        filas_dia = [f for f in todas if f.get("FECHA", "") == fecha]
        macros = _sumar_macros(filas_dia)
        cumplimiento = round(macros["kcal"] / objetivo["kcal"], 2) if objetivo.get("kcal") else 0
        dias.append({"fecha": fecha, **macros, "cumplimiento_kcal": cumplimiento})

    return {"objetivo": objetivo, "dias": dias}


# ---- historial entrenamientos ----

def _leer_historial_sync(limite: int = 30) -> dict:
    cliente = conectar()
    sesiones = _leer_hoja_sync(cliente, NOMBRE_HOJAS["historial_entrenamientos"])
    ejercicios = _leer_hoja_sync(cliente, NOMBRE_HOJAS["ejercicios_detalle"])

    # índice ejercicios por sesion_id para calcular volumen
    vol_por_sesion: dict[str, float] = {}
    for ej in ejercicios:
        sid = ej.get("SESION_ID", "")
        series = _to_num(ej.get("SERIES"))
        reps = _to_num(ej.get("REPS_REALIZADAS") or ej.get("REPS_OBJETIVO"))
        peso = _to_num(ej.get("PESO_KG"))
        vol_por_sesion[sid] = vol_por_sesion.get(sid, 0) + series * reps * peso

    resultado = []
    for s in reversed(sesiones[-limite:]):
        sid = s.get("SESION_ID", "")
        resultado.append({
            "sesion_id": sid,
            "fecha": s.get("FECHA", ""),
            "hora_inicio": s.get("HORA_INICIO", ""),
            "duracion_min": _to_num(s.get("DURACION_MIN")),
            "tipo_sesion": s.get("TIPO_SESION", ""),
            "grupo_muscular_principal": s.get("GRUPO_MUSCULAR_PRINCIPAL", ""),
            "nivel_energia": _to_num(s.get("NIVEL_ENERGIA_1_5")),
            "nivel_esfuerzo": _to_num(s.get("NIVEL_ESFUERZO_1_10")),
            "notas": s.get("NOTAS_SESION", ""),
            "volumen_total_kg": round(vol_por_sesion.get(sid, 0), 1),
        })

    return {"sesiones": resultado}


# ---- API async ----

async def leer_perfil() -> dict:
    return await asyncio.to_thread(_leer_perfil_sync)


async def guardar_perfil(campos: dict) -> None:
    await asyncio.to_thread(_guardar_perfil_sync, campos)


async def leer_rutina() -> dict:
    return await asyncio.to_thread(_leer_rutina_sync)


async def leer_historial(limite: int = 30) -> dict:
    return await asyncio.to_thread(_leer_historial_sync, limite)


async def leer_nutricion_hoy() -> dict:
    """Lee nutrición de hoy. Si no hay macros objetivo, los calcula con el LLM (lazy)."""
    objetivo = await leer_macros_objetivo_activos("dia")
    if objetivo is None:
        from engine.calcular_macros import calcular_macros_objetivo
        perfil = await leer_perfil()
        objetivo = await calcular_macros_objetivo(perfil)
        await guardar_macros_objetivo("dia", objetivo)

    return await asyncio.to_thread(_leer_nutricion_hoy_sync, objetivo)


async def leer_nutricion_semana() -> dict:
    """Lee nutrición de los últimos 7 días vs objetivo."""
    objetivo = await leer_macros_objetivo_activos("dia")
    if objetivo is None:
        from engine.calcular_macros import calcular_macros_objetivo
        perfil = await leer_perfil()
        objetivo = await calcular_macros_objetivo(perfil)
        await guardar_macros_objetivo("dia", objetivo)

    return await asyncio.to_thread(_leer_nutricion_semana_sync, objetivo)
