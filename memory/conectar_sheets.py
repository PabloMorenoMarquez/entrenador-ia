"""
Gestión de Google Sheets.
Lectura de contexto del usuario y escritura de conversaciones y memoria.
"""

import gspread
from google.oauth2.service_account import Credentials
import os
import json
import asyncio
from datetime import datetime

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",  # lectura y escritura
    "https://www.googleapis.com/auth/drive.readonly"
]

SHEET_ID = os.environ.get("SHEET_ID", "1j2iRn67xxU6BIs3hu8qnw7qO98mgGWuRsGiBp4tyf5U")

# Mapeo: nombre lógico de sheet → nombre real en Google Sheets
MAX_MEMORIA_PROMPT = 15  # máximo de entradas de memoria inyectadas al prompt

NOMBRE_HOJAS = {
    "perfil_usuario":    "perfil_usuario",
    "dias_tipicos":      "dias_tipicos",
    "plan_semanal":      "plan_semanal",
    "objetivos":         "objetivos",
    "alimentos_disponibles": "alimentos_disponibles",
    "memory":            "memory",
    "conversaciones":    "conversaciones",
    "ejercicios_detalle":    "ejercicios_detalle",
    "historial_entrenamientos": "historial_entrenamientos",
    "registro_comidas":  "registro_comidas",
    "macros_objetivo":   "macros_objetivo",
}


# ---- Conexión (cliente cacheado — una sola auth por proceso) ----

_cliente_cache = None
_spreadsheet_cache = None


def _cargar_credenciales() -> dict:
    """
    Carga credenciales de service account.
    Orden de prioridad:
      1. Env var GOOGLE_CREDENTIALS (JSON en una sola línea — usado en Render)
      2. Archivo apuntado por GOOGLE_CREDENTIALS_FILE (para dev local)
      3. Archivo 'service_account.json' en la raíz del proyecto (fallback dev)
    """
    cred_json = os.getenv("GOOGLE_CREDENTIALS", "").strip()
    if cred_json:
        try:
            return json.loads(cred_json)
        except json.JSONDecodeError:
            pass  # dotenv no pudo parsear JSON multilinea — probar archivo

    for ruta in [
        os.getenv("GOOGLE_CREDENTIALS_FILE", ""),
        "service_account.json",
    ]:
        if ruta and os.path.exists(ruta):
            with open(ruta, encoding="utf-8-sig") as f:
                return json.load(f)

    raise RuntimeError(
        "No se encontraron credenciales de Google. "
        "Configura GOOGLE_CREDENTIALS (JSON en una línea) o "
        "GOOGLE_CREDENTIALS_FILE=ruta/a/service_account.json"
    )


def conectar():
    """Devuelve cliente gspread autenticado. Reutiliza la conexión si ya existe."""
    global _cliente_cache
    if _cliente_cache is not None:
        return _cliente_cache
    credenciales_dict = _cargar_credenciales()
    creds = Credentials.from_service_account_info(credenciales_dict, scopes=SCOPES)
    _cliente_cache = gspread.authorize(creds)
    return _cliente_cache


# ---- Lectura ----

def _get_spreadsheet(cliente):
    """Devuelve el spreadsheet cacheado — evita llamada open_by_key por cada hoja."""
    global _spreadsheet_cache
    if _spreadsheet_cache is None:
        _spreadsheet_cache = cliente.open_by_key(SHEET_ID)
    return _spreadsheet_cache


def _leer_hoja_sync(cliente, nombre_hoja: str) -> list[dict]:
    """Lee todos los registros de una hoja."""
    try:
        hoja = _get_spreadsheet(cliente).worksheet(nombre_hoja)
        return hoja.get_all_records()
    except Exception as e:
        print(f"[sheets] Error leyendo '{nombre_hoja}': {e}")
        return []


def _hojas_a_texto(filas: list[dict]) -> str:
    """Convierte registros de una sheet en texto legible para el LLM."""
    if not filas:
        return ""
    return "\n".join(
        ", ".join(f"{k}: {v}" for k, v in fila.items() if v)
        for fila in filas
    )


_HOJAS_ESTATICAS = {
    "perfil_usuario", "dias_tipicos", "plan_semanal", "objetivos", "alimentos_disponibles",
}


def _leer_sheets_sync(nombres: list[str]) -> dict:
    """
    Lee varias sheets y las devuelve como dict {nombre: texto}.
    Hojas estáticas: Supabase configuracion primario, lazy-populate desde Sheets.
    Hojas dinámicas y memory: Sheets directo.
    """
    resultado = {}
    hojas_para_sheets = []

    # Intentar Supabase para hojas estáticas
    try:
        from db.repositorio import leer_configuracion_sb
        for nombre in nombres:
            if nombre in _HOJAS_ESTATICAS:
                cfg = leer_configuracion_sb(nombre)
                if cfg and cfg[0]:
                    resultado[nombre] = cfg[0]
                else:
                    hojas_para_sheets.append(nombre)
            else:
                hojas_para_sheets.append(nombre)
    except Exception as e:
        print(f"[sheets] Configuracion Supabase no disponible: {e}")
        hojas_para_sheets = list(nombres)

    if not hojas_para_sheets:
        return resultado

    cliente = conectar()
    for nombre in hojas_para_sheets:
        nombre_real = NOMBRE_HOJAS.get(nombre, nombre)
        filas = _leer_hoja_sync(cliente, nombre_real)

        if nombre == "memory":
            activas = [f for f in filas if str(f.get("ACTIVA", "")).upper() in ("TRUE", "1", "VERDADERO", "SI", "SÍ")]
            activas_ordenadas = sorted(activas, key=lambda x: int(x.get("PRIORIDAD", 0) or 0), reverse=True)
            texto = _hojas_a_texto(activas_ordenadas[:MAX_MEMORIA_PROMPT])
        else:
            texto = _hojas_a_texto(filas)

        resultado[nombre] = texto

        # Lazy-populate en Supabase para hojas estáticas
        if nombre in _HOJAS_ESTATICAS and texto:
            try:
                from db.repositorio import guardar_configuracion_sb
                datos_json = {str(f.get(list(f.keys())[0], i)): f for i, f in enumerate(filas)} if nombre != "perfil_usuario" else {}
                if nombre == "perfil_usuario":
                    datos_json = {fila[list(fila.keys())[0]].lower().strip(): list(fila.values())[1] for fila in filas if len(fila) >= 2}
                guardar_configuracion_sb(nombre, texto, datos_json)
            except Exception as e:
                print(f"[sheets] Error lazy-populate '{nombre}' en Supabase: {e}")

    return resultado


def _leer_conversaciones_sync(limite: int) -> list[dict]:
    """
    Lee las últimas N conversaciones. Supabase primario, Sheets fallback.
    """
    try:
        from db.repositorio import leer_conversaciones_sb
        rows = leer_conversaciones_sb(limite)
        if rows:
            return rows
    except Exception as e:
        print(f"[sheets] Conversaciones Supabase no disponible, usando Sheets: {e}")

    cliente = conectar()
    nombre_real = NOMBRE_HOJAS["conversaciones"]
    filas = _leer_hoja_sync(cliente, nombre_real)
    ultimas = filas[-limite:] if len(filas) > limite else filas
    return [
        {"rol": fila.get("ROL", "user"), "contenido": fila.get("CONTENIDO", "")}
        for fila in ultimas
        if fila.get("CONTENIDO")
    ]


# ---- Escritura ----

def _guardar_conversacion_sync(mensaje_usuario: str, respuesta_coach: str) -> None:
    """Guarda el turno actual. Supabase primario, Sheets secundario (dual-write)."""
    try:
        from db.repositorio import guardar_conversacion_sb
        guardar_conversacion_sb("user", mensaje_usuario)
        guardar_conversacion_sb("assistant", respuesta_coach)
    except Exception as e:
        print(f"[sheets] Error guardando conversación en Supabase: {e}")

    try:
        cliente = conectar()
        hoja = _get_spreadsheet(cliente).worksheet(NOMBRE_HOJAS["conversaciones"])
        timestamp = datetime.now().isoformat()
        hoja.append_row(["", timestamp, "user", mensaje_usuario])
        hoja.append_row(["", timestamp, "assistant", respuesta_coach])
    except Exception as e:
        print(f"[sheets] Error guardando conversación en Sheets: {e}")


def _guardar_memoria_sync(entrada: dict) -> None:
    """
    Guarda una entrada en la sheet de memory.
    entrada: { tipo, contenido, prioridad }
    """
    cliente = conectar()
    hoja = _get_spreadsheet(cliente).worksheet(NOMBRE_HOJAS["memory"])
    timestamp = datetime.now().isoformat()

    hoja.append_row([
        "",                           # ID (vacío, lo gestiona Sheets si tiene fórmula)
        entrada.get("tipo", "general").upper(),
        entrada.get("contenido", ""),
        entrada.get("prioridad", 3),
        "",                           # TAGS (vacío por ahora)
        timestamp,                    # FECHA_CREACION
        "TRUE",                       # ACTIVA
    ])


# ---- API async (usada por pipeline.py) ----

async def leer_sheets(nombres: list[str]) -> dict:
    """Lee las sheets indicadas y devuelve dict {nombre: texto}."""
    return await asyncio.to_thread(_leer_sheets_sync, nombres)


async def leer_conversaciones(limite: int = 10) -> list[dict]:
    """Devuelve los últimos N turnos de conversación."""
    return await asyncio.to_thread(_leer_conversaciones_sync, limite)


async def guardar_conversacion(mensaje_usuario: str, respuesta_coach: str) -> None:
    """Guarda el turno actual en la sheet de conversaciones."""
    await asyncio.to_thread(_guardar_conversacion_sync, mensaje_usuario, respuesta_coach)


async def guardar_memoria(entrada: dict) -> None:
    """Guarda una entrada en la sheet de memory."""
    await asyncio.to_thread(_guardar_memoria_sync, entrada)


def _guardar_entreno_sync(datos: dict) -> str:
    """
    Guarda sesión y ejercicios. Supabase primario, Sheets secundario (dual-write).
    Devuelve sesion_id generado.
    """
    ahora = datetime.now()
    sesion_id = ahora.strftime("%Y%m%d-%H%M%S")

    try:
        from db.repositorio import guardar_entreno_sb
        guardar_entreno_sb(datos, sesion_id)
    except Exception as e:
        print(f"[sheets] Error guardando entreno en Supabase: {e}")

    try:
        cliente = conectar()
        spreadsheet = _get_spreadsheet(cliente)
        fecha = ahora.strftime("%Y-%m-%d")
        hora = ahora.strftime("%H:%M")
        sesion = datos.get("sesion") or {}

        hoja_hist = spreadsheet.worksheet(NOMBRE_HOJAS["historial_entrenamientos"])
        hoja_hist.append_row([
            sesion_id, fecha, hora, "",
            sesion.get("duracion_min") or "",
            sesion.get("tipo_sesion") or "",
            sesion.get("grupo_muscular_principal") or "",
            "",
            sesion.get("nivel_energia") or "",
            sesion.get("nivel_esfuerzo") or "",
            "", sesion.get("notas") or "",
        ])

        hoja_ej = spreadsheet.worksheet(NOMBRE_HOJAS["ejercicios_detalle"])
        for orden, ej in enumerate(datos.get("ejercicios") or [], start=1):
            hoja_ej.append_row([
                sesion_id, fecha, orden,
                ej.get("ejercicio") or "",
                ej.get("grupo_muscular") or "",
                ej.get("series") or "",
                ej.get("reps_objetivo") or "",
                ej.get("reps_realizadas") or "",
                ej.get("peso_kg") or "",
                ej.get("tipo_peso") or "",
                ej.get("descanso_seg") or "",
                ej.get("rir") or "",
                ej.get("notas") or "",
            ])
    except Exception as e:
        print(f"[sheets] Error guardando entreno en Sheets: {e}")

    return sesion_id


def _decay_memoria_sync() -> int:
    """
    Marca ACTIVA=FALSE entradas antiguas según prioridad.
    Reglas: prioridad 1 → 7 días, prioridad 2 → 30 días, prioridad 3 → 90 días.
    Prioridad 4-5 nunca expira automáticamente.
    Devuelve número de entradas expiradas.
    """
    cliente = conectar()
    hoja = _get_spreadsheet(cliente).worksheet(NOMBRE_HOJAS["memory"])
    filas = hoja.get_all_values()
    if len(filas) < 2:
        return 0

    headers = [h.upper() for h in filas[0]]
    idx = {h: i for i, h in enumerate(headers)}

    col_activa = idx.get("ACTIVA")
    col_prioridad = idx.get("PRIORIDAD")
    col_fecha = idx.get("FECHA_CREACION")
    if col_activa is None or col_prioridad is None or col_fecha is None:
        return 0

    ahora = datetime.now()
    DIAS_POR_PRIORIDAD = {1: 7, 2: 30, 3: 90}

    updates = []
    for row_num, fila in enumerate(filas[1:], start=2):
        activa = fila[col_activa].upper() if len(fila) > col_activa else "TRUE"
        if activa not in ("TRUE", "1", "VERDADERO", "SI", "SÍ"):
            continue

        try:
            prioridad = int(fila[col_prioridad] or 3)
        except (ValueError, IndexError):
            prioridad = 3

        if prioridad > 3:
            continue

        try:
            fecha = datetime.fromisoformat(fila[col_fecha])
            edad_dias = (ahora - fecha).days
        except (ValueError, IndexError):
            continue

        limite = DIAS_POR_PRIORIDAD.get(prioridad, 90)
        if edad_dias > limite:
            import gspread.utils as gu
            cell = gu.rowcol_to_a1(row_num, col_activa + 1)
            updates.append({"range": cell, "values": [["FALSE"]]})

    if updates:
        hoja.batch_update(updates)
        print(f"[memoria] Decay: {len(updates)} entradas expiradas")

    return len(updates)


async def decay_memoria() -> int:
    """Expira entradas de memoria antiguas en background. Devuelve número expiradas."""
    return await asyncio.to_thread(_decay_memoria_sync)


async def guardar_entreno(datos: dict) -> str:
    """Guarda sesión y ejercicios en Sheets. Devuelve sesion_id."""
    return await asyncio.to_thread(_guardar_entreno_sync, datos)


def _guardar_comida_sync(datos: dict) -> int:
    """
    Guarda alimentos en registro_comidas. Supabase primario, Sheets secundario (dual-write).
    Devuelve número de filas escritas.
    """
    try:
        from db.repositorio import guardar_comidas_sb
        guardar_comidas_sb(datos)
    except Exception as e:
        print(f"[sheets] Error guardando comida en Supabase: {e}")

    alimentos = datos.get("alimentos") or []
    try:
        cliente = conectar()
        spreadsheet = _get_spreadsheet(cliente)
        ahora = datetime.now()
        fecha = ahora.strftime("%Y-%m-%d")
        hora = ahora.strftime("%H:%M")
        comida = datos.get("comida") or {}
        tipo_comida = comida.get("tipo_comida") or ""
        notas_comida = comida.get("notas") or ""
        hoja = spreadsheet.worksheet(NOMBRE_HOJAS["registro_comidas"])
        for alimento in alimentos:
            notas_fila = alimento.get("notas") or notas_comida
            hoja.append_row([
                fecha, hora, tipo_comida,
                alimento.get("alimento") or "",
                alimento.get("cantidad_g_ml") or "",
                alimento.get("calorias") or "",
                alimento.get("proteinas_g") or "",
                alimento.get("carbos_g") or "",
                alimento.get("grasas_g") or "",
                alimento.get("fibra_g") or "",
                notas_fila,
            ])
    except Exception as e:
        print(f"[sheets] Error guardando comida en Sheets: {e}")

    return len(alimentos)


async def guardar_comida(datos: dict) -> int:
    """Guarda alimentos en registro_comidas. Devuelve número de filas escritas."""
    return await asyncio.to_thread(_guardar_comida_sync, datos)


def _leer_macros_objetivo_activos_sync(periodo: str) -> dict | None:
    """
    Lee macros objetivo activos. Supabase primario, Sheets fallback.
    """
    try:
        from db.repositorio import leer_macros_objetivo_sb
        macros = leer_macros_objetivo_sb(periodo)
        if macros:
            return macros
    except Exception as e:
        print(f"[sheets] Macros Supabase no disponible, usando Sheets: {e}")

    cliente = conectar()
    filas = _leer_hoja_sync(cliente, NOMBRE_HOJAS["macros_objetivo"])
    for fila in reversed(filas):
        activa = str(fila.get("ACTIVA", "")).upper()
        if activa in ("TRUE", "1", "VERDADERO", "SI", "SÍ") and fila.get("PERIODO") == periodo:
            return {
                "kcal": _to_num(fila.get("KCAL")),
                "proteinas_g": _to_num(fila.get("PROTEINAS_G")),
                "carbos_g": _to_num(fila.get("CARBOS_G")),
                "grasas_g": _to_num(fila.get("GRASAS_G")),
                "notas": fila.get("NOTAS", ""),
                "fecha_calculo": fila.get("FECHA_CALCULO", ""),
            }
    return None


def _guardar_macros_objetivo_sync(periodo: str, macros: dict) -> None:
    """
    Guarda macros objetivo. Supabase primario, Sheets secundario (dual-write).
    """
    try:
        from db.repositorio import guardar_macros_objetivo_sb
        guardar_macros_objetivo_sb(periodo, macros)
    except Exception as e:
        print(f"[sheets] Error guardando macros en Supabase: {e}")

    try:
        cliente = conectar()
        spreadsheet = _get_spreadsheet(cliente)
        hoja = spreadsheet.worksheet(NOMBRE_HOJAS["macros_objetivo"])
        filas = hoja.get_all_values()

        if len(filas) > 1:
            headers = [h.upper() for h in filas[0]]
            idx = {h: i for i, h in enumerate(headers)}
            col_activa = idx.get("ACTIVA")
            col_periodo = idx.get("PERIODO")

            if col_activa is not None and col_periodo is not None:
                import gspread.utils as gu
                updates = []
                for row_num, fila in enumerate(filas[1:], start=2):
                    if len(fila) > col_periodo and fila[col_periodo] == periodo:
                        activa = fila[col_activa].upper() if len(fila) > col_activa else ""
                        if activa in ("TRUE", "1", "VERDADERO", "SI", "SÍ"):
                            cell = gu.rowcol_to_a1(row_num, col_activa + 1)
                            updates.append({"range": cell, "values": [["FALSE"]]})
                if updates:
                    hoja.batch_update(updates)

        timestamp = datetime.now().isoformat()
        hoja.append_row([
            timestamp,
            periodo,
            macros.get("kcal", ""),
            macros.get("proteinas_g", ""),
            macros.get("carbos_g", ""),
            macros.get("grasas_g", ""),
            macros.get("notas", ""),
            "TRUE",
        ])
    except Exception as e:
        print(f"[sheets] Error guardando macros en Sheets: {e}")


def _to_num(val):
    """Convierte string a int/float, o devuelve 0."""
    try:
        f = float(str(val).replace(",", "."))
        return int(f) if f == int(f) else f
    except (ValueError, TypeError):
        return 0


async def leer_macros_objetivo_activos(periodo: str = "dia") -> dict | None:
    """Devuelve macros objetivo activos para el periodo indicado, o None si no existen."""
    return await asyncio.to_thread(_leer_macros_objetivo_activos_sync, periodo)


async def guardar_macros_objetivo(periodo: str, macros: dict) -> None:
    """Persiste los macros objetivo para un periodo, desactivando el anterior."""
    await asyncio.to_thread(_guardar_macros_objetivo_sync, periodo, macros)


# ---- Uso directo (debug) ----

if __name__ == "__main__":
    cliente = conectar()
    datos = _leer_hoja_sync(cliente, "perfil_usuario")
    print(f"Filas leídas: {len(datos)}")
    if datos:
        print("Primera fila:", datos[0])
