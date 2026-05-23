import json
import numpy as np
from collections import defaultdict

# -----------------------------------------------
# MOTOR DE DECISIÓN v2 — Coach IA
# Análisis determinista de entrenamiento
# -----------------------------------------------

OBJETIVO = "recomposicion"  # hipertrofia / fuerza / recomposicion

# Umbrales según objetivo
UMBRALES = {
    "hipertrofia":    {"rir_minimo": 1, "rir_optimo": 2, "sesiones_estancamiento": 3},
    "fuerza":         {"rir_minimo": 2, "rir_optimo": 3, "sesiones_estancamiento": 4},
    "recomposicion":  {"rir_minimo": 1, "rir_optimo": 2, "sesiones_estancamiento": 3},
}

def calcular_volumen(series, reps, peso, rir=None):
    """
    Volumen real = series × reps × peso
    Ajustado por RIR: a menos RIR, más cerca del fallo,
    mayor estímulo real aunque el volumen bruto sea igual.
    """
    volumen_bruto = series * reps * peso
    if rir is not None:
        # Factor de proximidad al fallo: RIR 0 = 1.15, RIR 4 = 1.0
        factor_rir = 1 + max(0, (4 - rir)) * 0.05
        return volumen_bruto * factor_rir
    return volumen_bruto

def calcular_tendencia(valores):
    """
    Regresión lineal simple sobre los valores.
    Devuelve la pendiente — positiva = mejora, negativa = empeora.
    Más fiable que comparar solo primera vs última sesión.
    """
    if len(valores) < 2:
        return 0
    x = list(range(len(valores)))
    x_mean = sum(x) / len(x)
    y_mean = sum(valores) / len(valores)
    numerador = sum((x[i] - x_mean) * (valores[i] - y_mean) for i in range(len(x)))
    denominador = sum((x[i] - x_mean) ** 2 for i in range(len(x)))
    if denominador == 0:
        return 0
    return numerador / denominador

def analizar_rir(rirs, objetivo):
    """
    Analiza la evolución del RIR para detectar:
    - fatiga acumulada (RIR bajando)
    - capacidad de progresión (RIR alto = margen disponible)
    - cercanía al fallo (RIR bajo = intensidad alta)
    """
    if not rirs:
        return {"estado": "sin_datos", "margen_progresion": None}

    rir_actual = rirs[-1]
    tendencia_rir = calcular_tendencia(rirs)
    umbral = UMBRALES[objetivo]

    if tendencia_rir < -0.3 and rir_actual <= umbral["rir_minimo"]:
        return {
            "estado": "fatiga_acumulada",
            "margen_progresion": "bajo",
            "detalle": f"RIR bajando progresivamente hasta {rir_actual}"
        }
    elif rir_actual > umbral["rir_optimo"] + 1:
        return {
            "estado": "intensidad_baja",
            "margen_progresion": "alto",
            "detalle": f"RIR {rir_actual} — hay margen para subir carga"
        }
    else:
        return {
            "estado": "optimo",
            "margen_progresion": "medio",
            "detalle": f"RIR {rir_actual} dentro del rango óptimo para {objetivo}"
        }

def analizar_ejercicio(nombre, historial, objetivo=OBJETIVO):
    """
    Analiza el historial de un ejercicio y devuelve
    el estado actual con recomendación concreta.
    """
    if len(historial) < 2:
        return {"estado": "sin_datos", "razon": "Menos de 2 sesiones registradas"}

    ultimas = historial[-5:]  # Últimas 5 sesiones

    # Calcular volumen ajustado por RIR para cada sesión
    volumenes = [
        calcular_volumen(s["series"], s["reps_realizadas"], s["peso"], s.get("rir"))
        for s in ultimas
    ]
    rirs = [s["rir"] for s in ultimas if s.get("rir") is not None]

    # Tendencias
    tendencia_volumen = calcular_tendencia(volumenes)
    analisis_rir = analizar_rir(rirs, objetivo)

    umbral = UMBRALES[objetivo]

    # --- FATIGA (prioridad máxima) ---
    if analisis_rir["estado"] == "fatiga_acumulada":
        return {
            "estado": "fatiga",
            "recomendacion": "reducir volumen 20-30%, mantener intensidad",
            "razon": analisis_rir["detalle"],
            "alternativas": ["deload parcial", "reducir series", "bajar peso 10%"]
        }

    # --- ESTANCAMIENTO ---
    sesiones_sin_cambio = sum(
        1 for i in range(1, len(volumenes))
        if abs(volumenes[i] - volumenes[i-1]) < volumenes[i-1] * 0.02
    )
    estancado = sesiones_sin_cambio >= umbral["sesiones_estancamiento"] - 1

    if estancado:
        # Si hay margen de RIR, recomendar subir carga
        if analisis_rir["margen_progresion"] == "alto":
            recomendacion = "subir carga — hay margen de RIR disponible"
        else:
            recomendacion = "subir reps antes que peso"

        return {
            "estado": "estancado",
            "recomendacion": recomendacion,
            "razon": f"{sesiones_sin_cambio + 1} sesiones sin progresión significativa",
            "alternativas": ["subir 1-2 reps", "subir 2.5 kg", "cambiar variante"]
        }

    # --- PROGRESIÓN ---
    if tendencia_volumen > 0:
        return {
            "estado": "progresando",
            "recomendacion": "mantener progresión actual",
            "razon": f"Tendencia de volumen positiva (+{tendencia_volumen:.1f} kg·reps/sesión)",
            "alternativas": []
        }

    # --- ESTABLE ---
    return {
        "estado": "estable",
        "recomendacion": "intentar progresar la próxima sesión",
        "razon": "Sin cambios claros pero sin señales de fatiga",
        "alternativas": ["subir 2.5 kg", "añadir 1 rep por serie"]
    }

def analizar_sesion(nivel_energia, nivel_esfuerzo, duracion_min):
    """
    Detecta señales de sobreentrenamiento o mala recuperación
    en una sesión individual.
    """
    alertas = []
    if nivel_energia <= 2:
        alertas.append("energía muy baja — revisar sueño y nutrición pre-entreno")
    if nivel_esfuerzo >= 9:
        alertas.append("esfuerzo muy alto — riesgo de sobreentrenamiento acumulado")
    if duracion_min > 90:
        alertas.append("sesión demasiado larga — cortisol aumenta tras 75-90 min")
    return alertas

def generar_informe(ejercicios_data, sesiones_data, objetivo=OBJETIVO):
    """
    Genera el informe completo del motor de decisión.
    Este informe se inyecta en el system prompt del coach.
    """
    informe = {
        "objetivo": objetivo,
        "ejercicios": {},
        "alertas_sesion": [],
        "resumen": []
    }

    for ejercicio, historial in ejercicios_data.items():
        resultado = analizar_ejercicio(ejercicio, historial, objetivo)
        informe["ejercicios"][ejercicio] = resultado

        if resultado["estado"] in ["estancado", "fatiga"]:
            informe["resumen"].append(
                f"{ejercicio}: {resultado['estado']} — {resultado['recomendacion']}"
            )

    for sesion in sesiones_data:
        alertas = analizar_sesion(
            sesion["nivel_energia"],
            sesion["nivel_esfuerzo"],
            sesion["duracion_min"]
        )
        informe["alertas_sesion"].extend(alertas)

    return informe


# -----------------------------------------------
# TEST con datos de ejemplo
# -----------------------------------------------
if __name__ == "__main__":
    ejercicios_ejemplo = {
        "Press de banca": [
            {"fecha": "2025-01-01", "series": 4, "reps_realizadas": 8, "peso": 70, "rir": 2},
            {"fecha": "2025-01-08", "series": 4, "reps_realizadas": 8, "peso": 70, "rir": 2},
            {"fecha": "2025-01-15", "series": 4, "reps_realizadas": 8, "peso": 70, "rir": 1},
        ],
        "Peso muerto rumano": [
            {"fecha": "2025-01-01", "series": 4, "reps_realizadas": 8, "peso": 80, "rir": 3},
            {"fecha": "2025-01-08", "series": 4, "reps_realizadas": 8, "peso": 82, "rir": 2},
            {"fecha": "2025-01-15", "series": 4, "reps_realizadas": 8, "peso": 85, "rir": 2},
        ],
        "Dominadas": [
            {"fecha": "2025-01-01", "series": 4, "reps_realizadas": 6, "peso": 0, "rir": 1},
            {"fecha": "2025-01-08", "series": 4, "reps_realizadas": 6, "peso": 0, "rir": 1},
            {"fecha": "2025-01-15", "series": 4, "reps_realizadas": 6, "peso": 0, "rir": 0},
        ]
    }

    sesiones_ejemplo = [
        {"nivel_energia": 2, "nivel_esfuerzo": 9, "duracion_min": 95},
        {"nivel_energia": 4, "nivel_esfuerzo": 7, "duracion_min": 70},
    ]

    informe = generar_informe(ejercicios_ejemplo, sesiones_ejemplo)
    print(json.dumps(informe, ensure_ascii=False, indent=2))