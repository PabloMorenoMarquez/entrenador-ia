"""
API principal del entrenador IA.
Punto de entrada HTTP para todas las peticiones.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os

from pipeline import procesar_mensaje

app = FastAPI(title="Entrenador IA")

_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")


# ---- Modelos de request/response ----

class ChatRequest(BaseModel):
    mensaje: str


class ChatResponse(BaseModel):
    respuesta: str


class PerfilUpdateRequest(BaseModel):
    campos: dict


# ---- Rutas chat ----

@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(os.path.join(_static_dir, "index.html"))


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.mensaje or not request.mensaje.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    try:
        respuesta = await procesar_mensaje(request.mensaje.strip())
        return ChatResponse(respuesta=respuesta)

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"Servicio temporalmente no disponible: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.api_route("/ping", methods=["GET", "HEAD"])
async def ping():
    return {"status": "ok"}


# ---- Endpoints API REST para la SPA ----

@app.get("/api/perfil")
async def get_perfil():
    try:
        from memory.lectura_estructurada import leer_perfil
        return await leer_perfil()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/perfil")
async def post_perfil(request: PerfilUpdateRequest):
    try:
        from memory.lectura_estructurada import guardar_perfil
        await guardar_perfil(request.campos)
        from memory.lectura_estructurada import leer_perfil
        return await leer_perfil()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rutina")
async def get_rutina():
    try:
        from memory.lectura_estructurada import leer_rutina
        data = await leer_rutina()
        if not data.get("sesion_id"):
            raise HTTPException(status_code=404, detail="No hay sesiones registradas.")
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/nutricion/hoy")
async def get_nutricion_hoy():
    try:
        from memory.lectura_estructurada import leer_nutricion_hoy
        return await leer_nutricion_hoy()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/nutricion/semana")
async def get_nutricion_semana():
    try:
        from memory.lectura_estructurada import leer_nutricion_semana
        return await leer_nutricion_semana()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/historial")
async def get_historial():
    try:
        from memory.lectura_estructurada import leer_historial
        return await leer_historial()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---- Catch-all para BrowserRouter (debe ir al final) ----

@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    index = os.path.join(_static_dir, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="Not found")
