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
    Lee perfil_usuario. Supabase configuracion primario (datos_json), lazy-populate, Sheets fallback.
    """
    try:
        from db.repositorio import leer_configuracion_sb
        cfg = leer_configuracion_sb("perfil_usuario")
        if cfg and cfg[1]:  # datos_json no vacío
            return cfg[1]
    except Exception as e:
        print(f"[lectura] Perfil Supabase no disponible: {e}")

    cliente = conectar()
    hoja = _get_spreadsheet(cliente).worksheet(NOMBRE_HOJAS["perfil_usuario"])
    filas = hoja.get_all_values()
    resultado = {}
    for fila in filas:
        if len(fila) >= 2 and fila[0] and fila[0].lower() not in ("campo", "etiqueta", "clave", "key"):
            resultado[fila[0].lower().strip()] = fila[1].strip() if fila[1] else ""

    if resultado:
        try:
            from db.repositorio import guardar_configuracion_sb
            texto = "\n".join(f"{k}: {v}" for k, v in resultado.items() if v)
            guardar_configuracion_sb("perfil_usuario", texto, resultado)
        except Exception as e:
            print(f"[lectura] Error lazy-populate perfil en Supabase: {e}")

    return resultado


def _guardar_perfil_sync(campos: dict) -> None:
    """
    Actualiza campos en perfil_usuario. Dual-write: Supabase + Sheets.
    """
    # Supabase: leer perfil actual, mergear, guardar
    try:
        from db.repositorio import leer_configuracion_sb, guardar_configuracion_sb
        cfg = leer_configuracion_sb("perfil_usuario")
        perfil_actual = cfg[1] if (cfg and cfg[1]) else {}
        perfil_actual.update({k.lower().strip(): str(v) for k, v in campos.items()})
        texto = "\n".join(f"{k}: {v}" for k, v in perfil_actual.items() if v)
        guardar_configuracion_sb("perfil_usuario", texto, perfil_actual)
    except Exception as e:
        print(f"[lectura] Error guardando perfil en Supabase: {e}")

    try:
        import gspread.utils as gu
        cliente = conectar()
        hoja = _get_spreadsheet(cliente).worksheet(NOMBRE_HOJAS["perfil_usuario"])
        filas = hoja.get_all_values()

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
                cell = gu.rowcol_to_a1(row_num, 2)
                updates.append({"range": cell, "values": [[str(valor)]]})
            else:
                nuevos.append([campo, str(valor)])

        if updates:
            hoja.batch_update(updates)
        for fila_nueva in nuevos:
            hoja.append_row(fila_nueva)
    except Exception as e:
        print(f"[lectura] Error guardando perfil en Sheets: {e}")


# ---- rutina (última sesión de ejercicios_detalle) ----

def _leer_rutina_sync() -> dict:
    """
    Última sesión de ejercicios. Supabase primario, Sheets fallback.
    """
    try:
        from db.repositorio import leer_rutina_sb
        rutina = leer_rutina_sb()
        if rutina:
            return rutina
    except Exception as e:
        print(f"[lectura] Rutina Supabase no disponible: {e}")

    cliente = conectar()
    filas = _leer_hoja_sync(cliente, NOMBRE_HOJAS["ejercicios_detalle"])
    if not filas:
        return {"sesion_id": None, "fecha": None, "ejercicios": []}

    ultimo_sesion_id = ""
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


# ---- plan de rutina semanal (objetivo vs realidad) ----

DIAS_SEMANA = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


def _leer_rutina_plan_sync() -> dict:
    from db.repositorio import leer_rutina_plan_sb, leer_ultimas_ejecuciones_sb

    plan = leer_rutina_plan_sb()
    nombres = [ej["ejercicio"] for ejercicios in plan.values() for ej in ejercicios if ej.get("ejercicio")]
    ultimas = leer_ultimas_ejecuciones_sb(nombres)

    dias = {}
    for dia in DIAS_SEMANA:
        ejercicios = plan.get(dia, [])
        dias[dia] = [{
            **ej,
            "ultima_vez": ultimas.get(ej["ejercicio"].strip().lower()),
        } for ej in ejercicios]

    return {"dias": dias}


def _guardar_rutina_plan_dia_sync(dia_semana: str, ejercicios: list) -> None:
    from db.repositorio import guardar_rutina_plan_dia
    guardar_rutina_plan_dia(dia_semana, ejercicios)


async def leer_rutina_plan() -> dict:
    return await asyncio.to_thread(_leer_rutina_plan_sync)


async def guardar_rutina_plan_dia(dia_semana: str, ejercicios: list) -> None:
    if dia_semana not in DIAS_SEMANA:
        raise ValueError(f"Día inválido: '{dia_semana}'. Válidos: {DIAS_SEMANA}")
    await asyncio.to_thread(_guardar_rutina_plan_dia_sync, dia_semana, ejercicios)


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


def _leer_comidas_sync(desde: str = None, hasta: str = None) -> list[dict]:
    """Lee comidas desde Supabase (primario) o Sheets (fallback)."""
    try:
        from db.repositorio import leer_comidas_fecha_sb, leer_comidas_rango_sb
        if desde and hasta:
            rows = leer_comidas_rango_sb(desde, hasta)
        else:
            from datetime import date as _date
            rows = leer_comidas_fecha_sb(desde or _date.today().isoformat())
        if rows is not None:
            return [{
                "ID": r.get("id", ""),
                "FECHA": r.get("fecha", ""),
                "HORA": str(r.get("hora") or ""),
                "TIPO_COMIDA": r.get("tipo_comida", ""),
                "ALIMENTO": r.get("alimento", ""),
                "CANTIDAD_G_ML": r.get("cantidad_g_ml") or 0,
                "CALORIAS": r.get("calorias") or 0,
                "PROTEINAS_G": r.get("proteinas_g") or 0,
                "CARBOS_G": r.get("carbos_g") or 0,
                "GRASAS_G": r.get("grasas_g") or 0,
                "FIBRA_G": r.get("fibra_g") or 0,
                "NOTAS": r.get("notas", ""),
                "FUENTE_DATOS": r.get("fuente_datos", "estimado"),
                "ESTIMADO": r.get("estimado", True),
            } for r in rows]
    except Exception as e:
        print(f"[lectura] Comidas Supabase no disponible: {e}")

    cliente = conectar()
    return _leer_hoja_sync(cliente, NOMBRE_HOJAS["registro_comidas"])


def _leer_nutricion_hoy_sync(objetivo: dict) -> dict:
    hoy = date.today().isoformat()
    de_hoy = _leer_comidas_sync(desde=hoy)
    consumido = _sumar_macros(de_hoy)
    comidas = [
        {
            "id": f.get("ID", ""),
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
            "fuente_datos": f.get("FUENTE_DATOS", "estimado"),
            "estimado": f.get("ESTIMADO", True),
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
    desde = fechas_semana[0]
    hasta = fechas_semana[-1]
    todas = _leer_comidas_sync(desde=desde, hasta=hasta)

    dias = []
    for fecha in fechas_semana:
        filas_dia = [f for f in todas if f.get("FECHA", "") == fecha]
        macros = _sumar_macros(filas_dia)
        cumplimiento = round(macros["kcal"] / objetivo["kcal"], 2) if objetivo.get("kcal") else 0
        dias.append({"fecha": fecha, **macros, "cumplimiento_kcal": cumplimiento})

    return {"objetivo": objetivo, "dias": dias}


# ---- historial entrenamientos ----

def _leer_historial_sync(limite: int = 30) -> dict:
    """Historial de entrenamientos. Supabase primario, Sheets fallback."""
    try:
        from db.repositorio import leer_historial_sb
        hist = leer_historial_sb(limite)
        if hist.get("sesiones"):
            return hist
    except Exception as e:
        print(f"[lectura] Historial Supabase no disponible: {e}")

    cliente = conectar()
    sesiones = _leer_hoja_sync(cliente, NOMBRE_HOJAS["historial_entrenamientos"])
    ejercicios = _leer_hoja_sync(cliente, NOMBRE_HOJAS["ejercicios_detalle"])

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
