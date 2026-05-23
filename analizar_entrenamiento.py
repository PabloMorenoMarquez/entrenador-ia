import json
import os
from conectar_sheets import conectar, leer_hoja
from motor_decision import generar_informe

SHEET_ID = "1j2iRn67xxU6BIs3hu8qnw7qO98mgGWuRsGiBp4tyf5U"

def obtener_ejercicios(cliente):
    """
    Lee ejercicios_detalle de Sheets y los agrupa
    por nombre de ejercicio para el motor de decisión.
    """
    filas = leer_hoja(cliente, SHEET_ID, "ejercicios_detalle")
    
    ejercicios = {}
    for fila in filas:
        nombre = fila.get("EJERCICIO", "").strip()
        if not nombre:
            continue
        
        if nombre not in ejercicios:
            ejercicios[nombre] = []
        
        ejercicios[nombre].append({
            "fecha": fila.get("FECHA", ""),
            "series": int(fila.get("SERIES", 0) or 0),
            "reps_realizadas": int(fila.get("REPS_REALIZADAS", 0) or 0),
            "peso": float(fila.get("PESO_KG", 0) or 0),
            "rir": int(fila.get("RIR", 2) or 2)
        })
    
    return ejercicios

def obtener_sesiones(cliente):
    """
    Lee historial_entrenamientos de Sheets para
    detectar señales de sobreentrenamiento.
    """
    filas = leer_hoja(cliente, SHEET_ID, "historial_entrenamientos")
    
    # Últimas 5 sesiones
    ultimas = filas[-5:] if len(filas) >= 5 else filas
    
    sesiones = []
    for fila in ultimas:
        sesiones.append({
            "nivel_energia": int(fila.get("NIVEL_ENERGIA_1_5", 3) or 3),
            "nivel_esfuerzo": int(fila.get("NIVEL_ESFUERZO_1_10", 5) or 5),
            "duracion_min": int(fila.get("DURACION_MIN", 60) or 60)
        })
    
    return sesiones

if __name__ == "__main__":
    cliente = conectar()
    
    print("Leyendo datos de Sheets...")
    ejercicios = obtener_ejercicios(cliente)
    sesiones = obtener_sesiones(cliente)
    
    if not ejercicios:
        print("No hay ejercicios registrados todavía en Sheets.")
    else:
        print(f"Ejercicios encontrados: {list(ejercicios.keys())}")
        informe = generar_informe(ejercicios, sesiones)
        print("\n--- INFORME MOTOR DE DECISIÓN ---")
        print(json.dumps(informe, ensure_ascii=False, indent=2))