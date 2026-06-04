"""
Motor de análisis de entrenamiento.
Lee datos de Sheets y genera un informe con el motor de decisión.
"""

import json
import os
from memory.conectar_sheets import conectar, _leer_hoja_sync
from engine.motor_decision import generar_informe

SHEET_ID = os.environ.get("SHEET_ID", "1j2iRn67xxU6BIs3hu8qnw7qO98mgGWuRsGiBp4tyf5U")


def _obtener_ejercicios(cliente) -> dict:
    """Lee ejercicios_detalle y los agrupa por nombre de ejercicio."""
    filas = _leer_hoja_sync(cliente, "ejercicios_detalle")

    ejercicios = {}
    for fila in filas:
        nombre = fila.get("EJERCICIO", "").strip()
        if not nombre:
            continue

        if nombre not in ejercicios:
            ejercicios[nombre] = []

        ejercicios[nombre].append({
            "fecha":           fila.get("FECHA", ""),
            "series":          int(fila.get("SERIES", 0) or 0),
            "reps_realizadas": int(fila.get("REPS_REALIZADAS", 0) or 0),
            "peso":            float(fila.get("PESO_KG", 0) or 0),
            "rir":             int(fila.get("RIR", 2) or 2),
            "grupo_muscular":  fila.get("GRUPO_MUSCULAR", "desconocido"),
        })

    return ejercicios


def _obtener_sesiones(cliente) -> list[dict]:
    """Lee las últimas 5 sesiones para detectar señales de sobreentrenamiento."""
    filas = _leer_hoja_sync(cliente, "historial_entrenamientos")
    ultimas = filas[-5:] if len(filas) >= 5 else filas

    return [
        {
            "nivel_energia":  int(fila.get("NIVEL_ENERGIA_1_5", 3) or 3),
            "nivel_esfuerzo": int(fila.get("NIVEL_ESFUERZO_1_10", 5) or 5),
            "duracion_min":   int(fila.get("DURACION_MIN", 60) or 60),
        }
        for fila in ultimas
    ]


_OBJETIVOS_VALIDOS = {"hipertrofia", "fuerza", "recomposicion"}

def _extraer_objetivo(contexto_usuario: dict) -> str:
    """Extrae el objetivo principal del texto de la sheet 'objetivos'."""
    texto = (contexto_usuario or {}).get("objetivos", "") or ""
    texto_lower = texto.lower()
    for obj in _OBJETIVOS_VALIDOS:
        if obj in texto_lower:
            return obj
    return "recomposicion"  # default


def analizar_entrenamiento(contexto_usuario: dict = None) -> dict:
    """
    Función principal que usa el pipeline.
    Lee ejercicios_detalle e historial de Sheets, genera y devuelve el informe.
    El objetivo se extrae del contexto_usuario (sheet 'objetivos') en vez de hardcode.
    """
    try:
        objetivo = _extraer_objetivo(contexto_usuario)
        cliente = conectar()
        ejercicios = _obtener_ejercicios(cliente)
        sesiones = _obtener_sesiones(cliente)

        if not ejercicios:
            return {"resumen": ["Sin datos de entrenamiento registrados."]}

        return generar_informe(ejercicios, sesiones, objetivo=objetivo)

    except Exception as e:
        print(f"[analizar_entrenamiento] Error: {e}")
        return {"resumen": [f"Error al analizar entrenamiento: {str(e)}"]}


# ---- Uso directo (debug) ----

if __name__ == "__main__":
    print("Leyendo datos de Sheets...")
    informe = analizar_entrenamiento()

    if not informe.get("resumen"):
        print("No hay ejercicios registrados todavía.")
    else:
        print("\n--- INFORME MOTOR DE DECISIÓN ---")
        print(json.dumps(informe, ensure_ascii=False, indent=2))
