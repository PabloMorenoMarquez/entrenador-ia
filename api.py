from fastapi import FastAPI
from pydantic import BaseModel
from conectar_sheets import conectar, leer_hoja
from analizar_entrenamiento import obtener_ejercicios, obtener_sesiones
from motor_decision import generar_informe
from buscar_contexto import buscar_contexto
from supabase import create_client
import json
import os
import time
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
SHEET_ID = "1j2iRn67xxU6BIs3hu8qnw7qO98mgGWuRsGiBp4tyf5U"
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Caché de datos de Sheets
_cache = {
    "ejercicios": None,
    "sesiones": None,
    "ultimo_update": 0
}
CACHE_TTL = 300  # 5 minutos

class PreguntaRequest(BaseModel):
    pregunta: str

def obtener_datos_sheets():
    """Lee Sheets solo si han pasado más de 5 minutos desde la última lectura."""
    ahora = time.time()
    if ahora - _cache["ultimo_update"] > CACHE_TTL or _cache["ejercicios"] is None:
        print("Actualizando caché de Sheets...")
        cliente = conectar()
        _cache["ejercicios"] = obtener_ejercicios(cliente)
        _cache["sesiones"] = obtener_sesiones(cliente)
        _cache["ultimo_update"] = ahora
    return _cache["ejercicios"], _cache["sesiones"]

@app.get("/ping")
@app.head("/ping")
def ping():
    return {"status": "ok"}

@app.get("/motor")
def motor():
    ejercicios, sesiones = obtener_datos_sheets()
    if not ejercicios:
        return {"resumen": "Sin datos de entrenamiento registrados aún."}
    informe = generar_informe(ejercicios, sesiones)
    return informe

@app.post("/rag")
def rag(request: PreguntaRequest):
    contexto = buscar_contexto(request.pregunta)
    return {"contexto": contexto}

@app.post("/analisis-completo")
def analisis_completo(request: PreguntaRequest):
    inicio = time.time()

    # Motor de decisión con caché
    ejercicios, sesiones = obtener_datos_sheets()

    if ejercicios:
        informe_motor = generar_informe(ejercicios, sesiones)
        motor_texto = informe_motor
    else:
        informe_motor = None
        motor_texto = "Sin datos de entrenamiento registrados aún."

    # RAG
    contexto_rag = buscar_contexto(request.pregunta)
    chunks = [c for c in contexto_rag.split("[Fuente:") if c.strip()]

    # Duración
    duracion_ms = int((time.time() - inicio) * 1000)

    # Log
    try:
        supabase.table("logs").insert({
            "pregunta": request.pregunta,
            "motor_decision": informe_motor,
            "contexto_rag": contexto_rag,
            "chunks_encontrados": len(chunks),
            "duracion_ms": duracion_ms
        }).execute()
    except Exception as e:
        print(f"Error guardando log: {e}")

    return {
        "motor_decision": json.dumps(motor_texto, ensure_ascii=False) if isinstance(motor_texto, dict) else motor_texto,
        "contexto_cientifico": contexto_rag
    }