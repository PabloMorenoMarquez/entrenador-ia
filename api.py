from fastapi import FastAPI
from pydantic import BaseModel
from conectar_sheets import conectar, leer_hoja
from analizar_entrenamiento import obtener_ejercicios, obtener_sesiones
from motor_decision import generar_informe
from buscar_contexto import buscar_contexto
import json

app = FastAPI()

@app.get("/ping")
@app.head("/ping")
def ping():
    return {"status": "ok"}

SHEET_ID = "1j2iRn67xxU6BIs3hu8qnw7qO98mgGWuRsGiBp4tyf5U"

class PreguntaRequest(BaseModel):
    pregunta: str

@app.get("/motor")
def motor():
    """
    Lee tus datos reales de Sheets y devuelve
    el informe del motor de decisión.
    Make llama a este endpoint antes de llamar al coach.
    """
    cliente = conectar()
    ejercicios = obtener_ejercicios(cliente)
    sesiones = obtener_sesiones(cliente)

    if not ejercicios:
        return {"resumen": "Sin datos de entrenamiento registrados aún."}

    informe = generar_informe(ejercicios, sesiones)
    return informe

@app.post("/rag")
def rag(request: PreguntaRequest):
    """
    Recibe la pregunta del usuario y devuelve
    los chunks relevantes de los libros.
    Make llama a este endpoint para obtener
    el contexto científico antes de llamar al coach.
    """
    contexto = buscar_contexto(request.pregunta)
    return {"contexto": contexto}

@app.post("/analisis-completo")
def analisis_completo(request: PreguntaRequest):
    """
    Endpoint principal — une motor de decisión + RAG
    en una sola llamada. Make solo necesita llamar aquí.
    """
    # Motor de decisión
    cliente = conectar()
    ejercicios = obtener_ejercicios(cliente)
    sesiones = obtener_sesiones(cliente)

    if ejercicios:
        informe_motor = generar_informe(ejercicios, sesiones)
        motor_texto = json.dumps(informe_motor, ensure_ascii=False)
    else:
        motor_texto = "Sin datos de entrenamiento registrados aún."

    # RAG
    contexto_rag = buscar_contexto(request.pregunta)

    return {
        "motor_decision": motor_texto,
        "contexto_cientifico": contexto_rag
    }