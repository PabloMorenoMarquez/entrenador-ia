import json
from datetime import datetime, timedelta

# -----------------------------------------------
# MOTOR DE DECISIÓN v3 — Coach IA
# Sistema de scoring numérico + simulador de coach
# -----------------------------------------------

OBJETIVO = "recomposicion"  # hipertrofia / fuerza / recomposicion

UMBRALES = {
    "hipertrofia":   {"rir_minimo": 1, "rir_optimo": 2, "sesiones_estancamiento": 3, "volumen_min": 12, "volumen_max": 20},
    "fuerza":        {"rir_minimo": 2, "rir_optimo": 3, "sesiones_estancamiento": 4, "volumen_min": 6,  "volumen_max": 12},
    "recomposicion": {"rir_minimo": 1, "rir_optimo": 2, "sesiones_estancamiento": 3, "volumen_min": 10, "volumen_max": 18},
}

TIPO_EJERCICIO = {
    "compuesto": [
        "press de banca", "peso muerto", "dominadas", "remo", "press militar",
        "fondos", "sentadilla", "hack squat", "hip thrust", "peso muerto rumano",
        "press inclinado", "press declinado", "zancadas", "step up"
    ],
    "aislamiento": [
        "curl", "extensión", "aperturas", "elevaciones", "cruce de poleas",
        "patada de triceps", "martillo", "concentrado", "press francés"
    ]
}

# -----------------------------------------------
# UTILIDADES
# -----------------------------------------------

def calcular_volumen(series, reps, peso, rir=None):
    volumen_bruto = series * reps * peso
    if rir is not None:
        factor_rir = 1 + max(0, (4 - rir)) * 0.05
        return volumen_bruto * factor_rir
    return volumen_bruto

def calcular_tendencia(valores):
    if len(valores) < 2:
        return 0
    x = list(range(len(valores)))
    x_mean = sum(x) / len(x)
    y_mean = sum(valores) / len(valores)
    num = sum((x[i] - x_mean) * (valores[i] - y_mean) for i in range(len(x)))
    den = sum((x[i] - x_mean) ** 2 for i in range(len(x)))
    return num / den if den != 0 else 0

def detectar_tipo_ejercicio(nombre):
    nombre_lower = nombre.lower()
    for ejercicio in TIPO_EJERCICIO["compuesto"]:
        if ejercicio in nombre_lower:
            return "compuesto"
    for ejercicio in TIPO_EJERCICIO["aislamiento"]:
        if ejercicio in nombre_lower:
            return "aislamiento"
    return "compuesto"  # Default compuesto si no se detecta

# -----------------------------------------------
# SCORING
# -----------------------------------------------

def calcular_score_progresion(volumenes, pesos):
    if len(volumenes) < 2:
        return 50
    tendencia = calcular_tendencia(volumenes)
    volumen_medio = sum(volumenes) / len(volumenes)
    if volumen_medio == 0:
        return 50
    progresion_pct = (tendencia / volumen_medio) * 100
    score = 50 + (progresion_pct * 5)
    return max(0, min(100, score))

def calcular_score_fatiga(rirs, objetivo):
    if not rirs:
        return 0
    umbral = UMBRALES[objetivo]
    rir_actual = rirs[-1]
    tendencia_rir = calcular_tendencia(rirs)
    score_rir = max(0, (umbral["rir_optimo"] - rir_actual) * 25)
    score_tendencia = max(0, -tendencia_rir * 30)
    score = score_rir + score_tendencia
    return max(0, min(100, score))

def calcular_score_estancamiento(volumenes, objetivo):
    if len(volumenes) < 2:
        return 0
    umbral = UMBRALES[objetivo]
    sesiones_sin_cambio = sum(
        1 for i in range(1, len(volumenes))
        if abs(volumenes[i] - volumenes[i-1]) < volumenes[i-1] * 0.02
    )
    score = (sesiones_sin_cambio / umbral["sesiones_estancamiento"]) * 100
    return max(0, min(100, score))

def calcular_score_global(score_progresion, score_fatiga, score_estancamiento):
    """
    Score global ponderado 0-100.
    100 = óptimo, progresando sin fatiga
    0 = crítico, con fatiga y estancamiento
    """
    score = (
        score_progresion * 0.4
        - score_fatiga * 0.4
        - score_estancamiento * 0.2
    )
    # Normalizar a 0-100
    score_normalizado = 50 + score * 0.5
    return max(0, min(100, round(score_normalizado)))

def normalizar_volumen(volumenes):
    """
    Normaliza los volúmenes a escala 0-100
    para poder comparar ejercicios entre sí
    independientemente del peso usado.
    """
    if not volumenes or max(volumenes) == 0:
        return volumenes
    max_vol = max(volumenes)
    return [round((v / max_vol) * 100, 1) for v in volumenes]

# -----------------------------------------------
# ANÁLISIS POR EJERCICIO
# -----------------------------------------------

def analizar_ejercicio(nombre, historial, objetivo=OBJETIVO, fatiga_grupo=0):
    """
    fatiga_grupo: fatiga acumulada del grupo muscular
    procedente de otros ejercicios de la misma semana.
    """
    if len(historial) < 2:
        return {
            "estado": "sin_datos",
            "score_global": 50,
            "score_progresion": 50,
            "score_fatiga": 0,
            "score_estancamiento": 0,
            "tipo": detectar_tipo_ejercicio(nombre),
            "recomendacion": "Registra más sesiones para obtener análisis",
            "razon": "Menos de 2 sesiones registradas",
            "alternativas": []
        }

    ultimas = historial[-5:]
    tipo = detectar_tipo_ejercicio(nombre)

    volumenes = [calcular_volumen(s["series"], s["reps_realizadas"], s["peso"], s.get("rir")) for s in ultimas]
    pesos = [s["peso"] for s in ultimas]
    rirs = [s["rir"] for s in ultimas if s.get("rir") is not None]

    # Normalizar volúmenes para scoring justo
    volumenes_norm = normalizar_volumen(volumenes)

    # Scores individuales
    score_progresion = calcular_score_progresion(volumenes_norm, pesos)
    score_fatiga = calcular_score_fatiga(rirs, objetivo)
    score_estancamiento = calcular_score_estancamiento(volumenes_norm, objetivo)

    # Ajuste por tipo de ejercicio
    if tipo == "compuesto":
        score_fatiga = min(100, score_fatiga * 1.2)

    # Ajuste por fatiga acumulada del grupo muscular
    score_fatiga = min(100, score_fatiga + fatiga_grupo * 0.3)

    # Score global ponderado
    score_global = calcular_score_global(score_progresion, score_fatiga, score_estancamiento)

    # Decisión basada en score global y scores individuales
    if score_fatiga >= 70:
        estado = "fatiga"
        if tipo == "compuesto":
            recomendacion = "reducir volumen 20-30% y mantener intensidad — ejercicio compuesto, prioridad recuperación"
        else:
            recomendacion = "reducir series o bajar peso 10%"

    elif score_estancamiento >= 70:
        estado = "estancado"
        if rirs and rirs[-1] > UMBRALES[objetivo]["rir_optimo"]:
            recomendacion = "subir carga — hay margen de RIR disponible"
        else:
            recomendacion = "subir reps antes que peso"

    elif score_progresion >= 60:
        estado = "progresando"
        recomendacion = "mantener progresión actual"

    else:
        estado = "estable"
        recomendacion = "intentar progresar la próxima sesión"

    return {
        "estado": estado,
        "tipo": tipo,
        "score_global": score_global,
        "score_progresion": round(score_progresion),
        "score_fatiga": round(score_fatiga),
        "score_estancamiento": round(score_estancamiento),
        "recomendacion": recomendacion,
        "razon": f"Basado en últimas {len(ultimas)} sesiones",
        "alternativas": _alternativas(estado, tipo)
    }

def _alternativas(estado, tipo):
    if estado == "fatiga":
        return ["deload parcial", "reducir series", "bajar peso 10%"]
    elif estado == "estancado":
        if tipo == "compuesto":
            return ["subir 2.5 kg", "subir 1-2 reps", "cambiar variante"]
        else:
            return ["subir 1-2 reps", "reducir descanso", "cambiar ángulo"]
    return []

# -----------------------------------------------
# ANÁLISIS DE SESIÓN
# -----------------------------------------------

def analizar_sesion(nivel_energia, nivel_esfuerzo, duracion_min):
    alertas = []
    if nivel_energia <= 2:
        alertas.append("energía muy baja — revisar sueño y nutrición pre-entreno")
    if nivel_esfuerzo >= 9:
        alertas.append("esfuerzo muy alto — riesgo de sobreentrenamiento acumulado")
    if duracion_min > 90:
        alertas.append("sesión demasiado larga — cortisol aumenta tras 75-90 min")
    return alertas

# -----------------------------------------------
# ANÁLISIS DE VOLUMEN SEMANAL
# -----------------------------------------------

VOLUMEN_OPTIMO = {
    "hipertrofia":   {"minimo": 12, "maximo": 20},
    "fuerza":        {"minimo": 6,  "maximo": 12},
    "recomposicion": {"minimo": 10, "maximo": 18},
}

def analizar_volumen_semanal(ejercicios_data, objetivo=OBJETIVO):
    hoy = datetime.now()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_semana = inicio_semana.replace(hour=0, minute=0, second=0, microsecond=0)

    volumen_por_grupo = {}

    for ejercicio, historial in ejercicios_data.items():
        for sesion in historial:
            try:
                fecha = datetime.strptime(sesion["fecha"], "%Y-%m-%d")
            except:
                continue
            if fecha < inicio_semana:
                continue
            grupo = sesion.get("grupo_muscular", "desconocido").strip().lower()
            series = sesion.get("series", 0)
            if grupo not in volumen_por_grupo:
                volumen_por_grupo[grupo] = 0
            volumen_por_grupo[grupo] += series

    limites = VOLUMEN_OPTIMO[objetivo]
    analisis = {}
    alertas = []

    for grupo, series_totales in volumen_por_grupo.items():
        if series_totales < limites["minimo"]:
            estado = "bajo"
            alertas.append(f"{grupo}: {series_totales} series — por debajo del mínimo ({limites['minimo']})")
        elif series_totales > limites["maximo"]:
            estado = "excesivo"
            alertas.append(f"{grupo}: {series_totales} series — por encima del máximo ({limites['maximo']}), riesgo fatiga")
        else:
            estado = "optimo"

        analisis[grupo] = {
            "series_semana": series_totales,
            "estado": estado
        }

    return {"volumen_semanal": analisis, "alertas_volumen": alertas}

# -----------------------------------------------
# SIMULADOR DE COACH (sin IA)
# -----------------------------------------------

def generar_texto_coach(informe):
    """
    Genera recomendaciones en texto plano basadas
    en el informe del motor. Sin IA, lógica pura.
    """
    lineas = []
    lineas.append("=== ANÁLISIS DE ENTRENAMIENTO ===\n")

    # Alertas de sesión
    if informe["alertas_sesion"]:
        lineas.append("⚠️ ALERTAS:")
        for alerta in informe["alertas_sesion"]:
            lineas.append(f"  - {alerta}")
        lineas.append("")

    # Alertas de volumen
    if informe["alertas_volumen"]:
        lineas.append("📊 VOLUMEN SEMANAL:")
        for alerta in informe["alertas_volumen"]:
            lineas.append(f"  - {alerta}")
        lineas.append("")

    # Ejercicios
    lineas.append("🏋️ EJERCICIOS:")
    for ejercicio, datos in informe["ejercicios"].items():
        if datos["estado"] == "sin_datos":
            continue

        emoji = {
            "progresando": "✅",
            "estable": "➡️",
            "estancado": "⚠️",
            "fatiga": "🔴"
        }.get(datos["estado"], "➡️")

        lineas.append(f"\n  {emoji} {ejercicio} ({datos['tipo']})")
        lineas.append(f"     Estado: {datos['estado'].upper()}")
        lineas.append(f"     Scores → Progresión: {datos['score_progresion']}/100 | Fatiga: {datos['score_fatiga']}/100 | Estancamiento: {datos['score_estancamiento']}/100")
        lineas.append(f"     Recomendación: {datos['recomendacion']}")
        if datos["alternativas"]:
            lineas.append(f"     Alternativas: {', '.join(datos['alternativas'])}")

    # Resumen
    if informe["resumen"]:
        lineas.append("\n📋 RESUMEN:")
        for item in informe["resumen"]:
            lineas.append(f"  - {item}")

    return "\n".join(lineas)

# -----------------------------------------------
# INFORME COMPLETO
# -----------------------------------------------

def generar_informe(ejercicios_data, sesiones_data, objetivo=OBJETIVO):
    informe = {
        "objetivo": objetivo,
        "ejercicios": {},
        "alertas_sesion": [],
        "alertas_volumen": [],
        "volumen_semanal": {},
        "resumen": []
    }

    # Calcular fatiga acumulada por grupo muscular
    # basada en volumen semanal de cada grupo
    fatiga_por_grupo = {}
    volumen = analizar_volumen_semanal(ejercicios_data, objetivo)
    for grupo, datos in volumen["volumen_semanal"].items():
        limites = VOLUMEN_OPTIMO[objetivo]
        series = datos["series_semana"]
        # Fatiga acumulada proporcional al volumen sobre el mínimo
        fatiga_por_grupo[grupo] = max(0, (series - limites["minimo"]) / limites["minimo"] * 100)

    # Analizar cada ejercicio con fatiga de grupo
    for ejercicio, historial in ejercicios_data.items():
        # Obtener grupo muscular del historial
        grupo = historial[-1].get("grupo_muscular", "desconocido").lower() if historial else "desconocido"
        fatiga_grupo = fatiga_por_grupo.get(grupo, 0)

        resultado = analizar_ejercicio(ejercicio, historial, objetivo, fatiga_grupo)
        informe["ejercicios"][ejercicio] = resultado

        if resultado["estado"] in ["estancado", "fatiga"]:
            informe["resumen"].append(
                f"{ejercicio} (score {resultado['score_global']}/100): {resultado['estado']} — {resultado['recomendacion']}"
            )

    for sesion in sesiones_data:
        alertas = analizar_sesion(
            sesion["nivel_energia"],
            sesion["nivel_esfuerzo"],
            sesion["duracion_min"]
        )
        informe["alertas_sesion"].extend(alertas)

    informe["volumen_semanal"] = volumen["volumen_semanal"]
    informe["alertas_volumen"] = volumen["alertas_volumen"]
    informe["resumen"].extend(volumen["alertas_volumen"])

    return informe

# -----------------------------------------------
# TEST
# -----------------------------------------------

if __name__ == "__main__":
    ejercicios_ejemplo = {
        "Press de banca": [
            {"fecha": "2025-01-01", "series": 4, "reps_realizadas": 8, "peso": 70, "rir": 2, "grupo_muscular": "pecho"},
            {"fecha": "2025-01-08", "series": 4, "reps_realizadas": 8, "peso": 70, "rir": 2, "grupo_muscular": "pecho"},
            {"fecha": "2025-01-15", "series": 4, "reps_realizadas": 8, "peso": 70, "rir": 1, "grupo_muscular": "pecho"},
        ],
        "Peso muerto rumano": [
            {"fecha": "2025-01-01", "series": 4, "reps_realizadas": 8, "peso": 80, "rir": 3, "grupo_muscular": "isquios"},
            {"fecha": "2025-01-08", "series": 4, "reps_realizadas": 8, "peso": 82, "rir": 2, "grupo_muscular": "isquios"},
            {"fecha": "2025-01-15", "series": 4, "reps_realizadas": 8, "peso": 85, "rir": 2, "grupo_muscular": "isquios"},
        ],
        "Curl de bíceps": [
            {"fecha": "2025-01-01", "series": 3, "reps_realizadas": 12, "peso": 15, "rir": 2, "grupo_muscular": "biceps"},
            {"fecha": "2025-01-08", "series": 3, "reps_realizadas": 12, "peso": 15, "rir": 1, "grupo_muscular": "biceps"},
            {"fecha": "2025-01-15", "series": 3, "reps_realizadas": 12, "peso": 15, "rir": 0, "grupo_muscular": "biceps"},
        ]
    }

    sesiones_ejemplo = [
        {"nivel_energia": 2, "nivel_esfuerzo": 9, "duracion_min": 95},
        {"nivel_energia": 4, "nivel_esfuerzo": 7, "duracion_min": 70},
    ]

    informe = generar_informe(ejercicios_ejemplo, sesiones_ejemplo)
    print(generar_texto_coach(informe))
    print("\n--- JSON COMPLETO ---")
    print(json.dumps(informe, ensure_ascii=False, indent=2))