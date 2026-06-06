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


def _obtener_sesiones(cliente, limite: int = 20) -> list[dict]:
    """Lee las últimas N sesiones. Ventana ampliada para análisis de largo plazo."""
    filas = _leer_hoja_sync(cliente, "historial_entrenamientos")
    ultimas = filas[-limite:] if len(filas) >= limite else filas

    return [
        {
            "fecha":          fila.get("FECHA", ""),
            "nivel_energia":  int(fila.get("NIVEL_ENERGIA_1_5", 3) or 3),
            "nivel_esfuerzo": int(fila.get("NIVEL_ESFUERZO_1_10", 5) or 5),
            "duracion_min":   int(fila.get("DURACION_MIN", 60) or 60),
        }
        for fila in ultimas
    ]


_MAPA_OBJETIVOS = {
    "hipertrofia":   ["hipertrofia", "ganar músculo", "ganar musculo", "masa muscular", "volumen"],
    "fuerza":        ["fuerza", "strength", "powerlifting", "1rm", "levantar más"],
    "recomposicion": ["recomposicion", "recomposición", "perder grasa", "definicion", "definición",
                      "perder peso", "grasa y músculo", "grasa y musculo"],
}

def _extraer_objetivo(contexto_usuario: dict) -> str:
    """Extrae el objetivo del texto de la sheet 'objetivos' usando keyword matching."""
    texto = (contexto_usuario or {}).get("objetivos", "") or ""
    texto_lower = texto.lower()
    for objetivo, palabras in _MAPA_OBJETIVOS.items():
        if any(p in texto_lower for p in palabras):
            return objetivo
    return "recomposicion"  # default razonable si no hay match


def analizar_entrenamiento(contexto_usuario: dict = None) -> dict:
    """
    Función principal que usa el pipeline.
    Lee ejercicios_detalle e historial de Sheets, genera el informe del motor
    y añade contexto de periodización (mesociclo actual + estancamiento largo plazo).
    """
    try:
        objetivo = _extraer_objetivo(contexto_usuario)
        cliente = conectar()
        ejercicios = _obtener_ejercicios(cliente)
        sesiones = _obtener_sesiones(cliente, limite=20)

        if not ejercicios:
            return {"resumen": ["Sin datos de entrenamiento registrados."]}

        # Informe base del motor reactivo (últimas 5 sesiones por ejercicio)
        informe = generar_informe(ejercicios, sesiones[-5:], objetivo=objetivo)

        # Periodización: plan activo + transición si procede
        try:
            from engine.periodizacion import (
                obtener_o_crear_plan,
                evaluar_transicion,
                aplicar_transicion,
                analizar_estancamiento_largo,
                resumen_periodizacion,
            )
            plan = obtener_o_crear_plan(objetivo)
            estado_global = informe.get("estado_global") or {}

            # Verificar si toca transición de fase
            decision = evaluar_transicion(plan, estado_global, objetivo)
            if decision in ("deload_urgente", "transicion_programada"):
                plan = aplicar_transicion(plan, objetivo, motivo=decision)

            # Estancamiento a largo plazo (ventana ampliada: 5 semanas)
            estancados = analizar_estancamiento_largo(ejercicios)

            # Añadir contexto de periodización al informe
            informe["periodizacion"] = {
                "fase": plan.get("fase"),
                "semana_inicio": plan.get("semana_inicio"),
                "duracion_semanas": plan.get("duracion_semanas"),
                "objetivo_volumen": plan.get("objetivo_volumen"),
                "estancados_largo_plazo": estancados,
                "resumen_texto": resumen_periodizacion(plan, objetivo, estancados),
            }

        except Exception as e_peri:
            print(f"[analizar_entrenamiento] Periodización no disponible (no crítico): {e_peri}")

        return informe

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
