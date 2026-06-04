"""
API principal del entrenador IA.
Punto de entrada HTTP para todas las peticiones.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from pipeline import procesar_mensaje

app = FastAPI(title="Entrenador IA")


# ---- Modelos de request/response ----

class ChatRequest(BaseModel):
    mensaje: str


class ChatResponse(BaseModel):
    respuesta: str


# ---- Rutas ----

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Ruta principal de conversación.
    Recibe un mensaje y devuelve la respuesta del coach.
    """
    if not request.mensaje or not request.mensaje.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    try:
        respuesta = await procesar_mensaje(request.mensaje.strip())
        return ChatResponse(respuesta=respuesta)

    except RuntimeError as e:
        # Todos los modelos fallaron (429 generalizado, etc.)
        raise HTTPException(
            status_code=503,
            detail=f"Servicio temporalmente no disponible: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@app.get("/health")
async def health():
    return {"status": "ok"}
