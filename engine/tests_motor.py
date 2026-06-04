import json
from engine.motor_decision import generar_informe, analizar_ejercicio

# -----------------------------------------------
# TESTS DEL MOTOR DE DECISIÓN
# -----------------------------------------------

def test(nombre, resultado, esperado):
    ok = resultado == esperado
    estado = "✅" if ok else "❌"
    print(f"{estado} {nombre}")
    if not ok:
        print(f"   Esperado: {esperado}")
        print(f"   Obtenido: {resultado}")

def run_tests():
    print("=== TESTS MOTOR DE DECISIÓN ===\n")

    # --- TEST 1: Progresión clara ---
    historial_progresion = [
        {"fecha": "2025-01-01", "series": 4, "reps_realizadas": 8, "peso": 60, "rir": 3, "grupo_muscular": "pecho"},
        {"fecha": "2025-01-08", "series": 4, "reps_realizadas": 8, "peso": 65, "rir": 3, "grupo_muscular": "pecho"},
        {"fecha": "2025-01-15", "series": 4, "reps_realizadas": 8, "peso": 70, "rir": 2, "grupo_muscular": "pecho"},
    ]
    resultado = analizar_ejercicio("Press de banca", historial_progresion)
    test("Progresión clara → estado progresando", resultado["estado"], "progresando")

    # --- TEST 2: Estancamiento claro ---
    historial_estancado = [
        {"fecha": "2025-01-01", "series": 4, "reps_realizadas": 8, "peso": 70, "rir": 2, "grupo_muscular": "pecho"},
        {"fecha": "2025-01-08", "series": 4, "reps_realizadas": 8, "peso": 70, "rir": 2, "grupo_muscular": "pecho"},
        {"fecha": "2025-01-15", "series": 4, "reps_realizadas": 8, "peso": 70, "rir": 2, "grupo_muscular": "pecho"},
        {"fecha": "2025-01-22", "series": 4, "reps_realizadas": 8, "peso": 70, "rir": 2, "grupo_muscular": "pecho"},
    ]
    resultado = analizar_ejercicio("Press de banca", historial_estancado)
    test("Estancamiento claro → estado estancado", resultado["estado"], "estancado")

    # --- TEST 3: Fatiga por RIR ---
    historial_fatiga = [
        {"fecha": "2025-01-01", "series": 4, "reps_realizadas": 8, "peso": 70, "rir": 3, "grupo_muscular": "pecho"},
        {"fecha": "2025-01-08", "series": 4, "reps_realizadas": 8, "peso": 70, "rir": 2, "grupo_muscular": "pecho"},
        {"fecha": "2025-01-15", "series": 4, "reps_realizadas": 8, "peso": 70, "rir": 0, "grupo_muscular": "pecho"},
    ]
    resultado = analizar_ejercicio("Press de banca", historial_fatiga)
    test("Fatiga por RIR bajando a 0 → estado fatiga", resultado["estado"], "fatiga")

    # --- TEST 4: Sin datos suficientes ---
    historial_corto = [
        {"fecha": "2025-01-01", "series": 4, "reps_realizadas": 8, "peso": 70, "rir": 2, "grupo_muscular": "pecho"},
    ]
    resultado = analizar_ejercicio("Press de banca", historial_corto)
    test("Una sola sesión → estado sin_datos", resultado["estado"], "sin_datos")

    # --- TEST 5: Score global coherente en progresión ---
    resultado = analizar_ejercicio("Peso muerto", historial_progresion)
    test("Progresión → score global > 50", resultado["score_global"] > 50, True)

    # --- TEST 6: Score global bajo en fatiga ---
    resultado = analizar_ejercicio("Press de banca", historial_fatiga)
    test("Fatiga → score_fatiga > score_progresion", resultado["score_fatiga"] > resultado["score_progresion"], True)

    # --- TEST 7: Compuesto tiene más penalización de fatiga que aislamiento ---
    resultado_compuesto = analizar_ejercicio("Press de banca", historial_fatiga)
    resultado_aislamiento = analizar_ejercicio("Curl de bíceps", historial_fatiga)
    test("Compuesto tiene más fatiga que aislamiento con mismos datos",
         resultado_compuesto["score_fatiga"] >= resultado_aislamiento["score_fatiga"], True)

    # --- TEST 8: Informe completo sin datos ---
    informe = generar_informe({}, [])
    test("Informe vacío no falla", isinstance(informe, dict), True)

    # --- TEST 9: Alertas de sesión ---
    sesiones = [{"nivel_energia": 1, "nivel_esfuerzo": 10, "duracion_min": 100}]
    informe = generar_informe({}, sesiones)
    test("Sesión extrema genera 3 alertas", len(informe["alertas_sesion"]), 3)

    # --- TEST 10: Sesión normal no genera alertas ---
    sesiones_normales = [{"nivel_energia": 4, "nivel_esfuerzo": 7, "duracion_min": 60}]
    informe = generar_informe({}, sesiones_normales)
    test("Sesión normal no genera alertas", len(informe["alertas_sesion"]), 0)

    # Añade estos tests al final de run_tests(), antes del print final

    # --- TEST 11: Peso 0 (ejercicios con peso corporal como dominadas) ---
    historial_peso_cero = [
        {"fecha": "2025-01-01", "series": 4, "reps_realizadas": 6, "peso": 0, "rir": 2, "grupo_muscular": "espalda"},
        {"fecha": "2025-01-08", "series": 4, "reps_realizadas": 7, "peso": 0, "rir": 2, "grupo_muscular": "espalda"},
        {"fecha": "2025-01-15", "series": 4, "reps_realizadas": 8, "peso": 0, "rir": 1, "grupo_muscular": "espalda"},
    ]
    resultado = analizar_ejercicio("Dominadas", historial_peso_cero)
    test("Peso 0 no falla (dominadas)", resultado["estado"] != "sin_datos", True)

    # --- TEST 12: RIR None en algunos registros ---
    historial_rir_none = [
        {"fecha": "2025-01-01", "series": 4, "reps_realizadas": 8, "peso": 70, "rir": None, "grupo_muscular": "pecho"},
        {"fecha": "2025-01-08", "series": 4, "reps_realizadas": 8, "peso": 72, "rir": None, "grupo_muscular": "pecho"},
        {"fecha": "2025-01-15", "series": 4, "reps_realizadas": 8, "peso": 75, "rir": None, "grupo_muscular": "pecho"},
    ]
    resultado = analizar_ejercicio("Press de banca", historial_rir_none)
    test("RIR None no falla", resultado["estado"] != "sin_datos", True)

    # --- TEST 13: Muchas sesiones (10+) ---
    historial_largo = [
        {"fecha": f"2025-0{i//10+1}-{i%28+1:02d}", "series": 4, "reps_realizadas": 8,
         "peso": 70 + i, "rir": 2, "grupo_muscular": "pecho"}
        for i in range(12)
    ]
    resultado = analizar_ejercicio("Press de banca", historial_largo)
    test("10+ sesiones no falla y usa solo últimas 5", resultado["razon"], "Basado en últimas 5 sesiones")

    # --- TEST 14: Regresión de peso ---
    historial_regresion = [
        {"fecha": "2025-01-01", "series": 4, "reps_realizadas": 8, "peso": 80, "rir": 2, "grupo_muscular": "pecho"},
        {"fecha": "2025-01-08", "series": 4, "reps_realizadas": 8, "peso": 75, "rir": 2, "grupo_muscular": "pecho"},
        {"fecha": "2025-01-15", "series": 4, "reps_realizadas": 8, "peso": 70, "rir": 2, "grupo_muscular": "pecho"},
    ]
    resultado = analizar_ejercicio("Press de banca", historial_regresion)
    test("Regresión → score progresión < 50", resultado["score_progresion"] < 50, True)

    # --- TEST 15: Score global siempre entre 0 y 100 ---
    for ejercicio, historial in [
        ("Press de banca", historial_progresion),
        ("Press de banca", historial_estancado),
        ("Press de banca", historial_fatiga),
        ("Dominadas", historial_peso_cero),
    ]:
        resultado = analizar_ejercicio(ejercicio, historial)
        test(f"Score global 0-100 en {resultado['estado']}",
             0 <= resultado["score_global"] <= 100, True)
        
    
    # --- TEST 19: Estado global existe en informe ---
    ejercicios_test = {
        "Press de banca": [
            {"fecha": "2025-01-01", "series": 4, "reps_realizadas": 8, "peso": 70, "rir": 2, "grupo_muscular": "pecho"},
            {"fecha": "2025-01-08", "series": 4, "reps_realizadas": 8, "peso": 72, "rir": 2, "grupo_muscular": "pecho"},
        ]
    }
    sesiones_test = [{"nivel_energia": 4, "nivel_esfuerzo": 7, "duracion_min": 60}]
    informe = generar_informe(ejercicios_test, sesiones_test)
    test("Estado global presente en informe", "estado_global" in informe, True)

    # --- TEST 20: Score global entre 0 y 100 ---
    test("Score global entre 0 y 100",
         0 <= informe["estado_global"]["score_global"] <= 100, True)

    # --- TEST 21: Sesión perfecta mejor que sesión mala ---
    sesiones_perfectas = [{"nivel_energia": 5, "nivel_esfuerzo": 7, "duracion_min": 60}]
    sesiones_malas = [{"nivel_energia": 1, "nivel_esfuerzo": 10, "duracion_min": 100}]
    informe_bueno = generar_informe(ejercicios_test, sesiones_perfectas)
    informe_malo = generar_informe(ejercicios_test, sesiones_malas)
    test("Sesión perfecta → mejor score global que sesión mala",
         informe_bueno["estado_global"]["score_global"] > informe_malo["estado_global"]["score_global"], True)

    print("\n=== FIN DE TESTS ===")

if __name__ == "__main__":
    run_tests()