"""
API principal del entrenador IA.
Punto de entrada HTTP para todas las peticiones.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import os
import asyncio
import uuid

from pipeline import procesar_mensaje

app = FastAPI(title="Entrenador IA")

_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")


# ---- Modelos de request/response ----

class ChatRequest(BaseModel):
    mensaje: str
    chat_id: Optional[str] = None


class ChatResponse(BaseModel):
    respuesta: str
    chat_id: str


class PerfilUpdateRequest(BaseModel):
    campos: dict


# ---- Modelos Fase 1: recuperación y biométricos ----

class BiometricosRequest(BaseModel):
    fecha: Optional[str] = None
    fuente: str = "manual"
    # Sueño
    sueno_horas: Optional[float] = None
    sueno_calidad: Optional[int] = None
    hora_acostarse: Optional[str] = None
    hora_despertar: Optional[str] = None
    rem_min: Optional[int] = None
    profundo_min: Optional[int] = None
    # Watch / sensores
    fc_reposo: Optional[int] = None
    hrv: Optional[int] = None
    spo2: Optional[float] = None
    pasos: Optional[int] = None
    estres: Optional[int] = None
    kcal_activas: Optional[int] = None


class CheckinRequest(BaseModel):
    fecha: Optional[str] = None
    fatiga: Optional[int] = None          # 1-5
    dolor_muscular: Optional[int] = None  # 1-5
    calidad_sueno: Optional[int] = None   # 1-5
    estado_mental: Optional[int] = None   # 1-5
    notas: Optional[str] = None


class MedidasRequest(BaseModel):
    fecha: Optional[str] = None
    peso_kg: Optional[float] = None
    cintura_cm: Optional[float] = None
    pecho_cm: Optional[float] = None
    brazo_cm: Optional[float] = None
    pierna_cm: Optional[float] = None
    grasa_pct: Optional[float] = None


class HidratacionRequest(BaseModel):
    litros: float
    fecha: Optional[str] = None


class DolorRequest(BaseModel):
    zona: str
    intensidad: int   # 0-10
    notas: Optional[str] = ""
    fecha: Optional[str] = None


class RutinaPlanEjercicio(BaseModel):
    ejercicio: str
    grupo_muscular: Optional[str] = None
    series_objetivo: Optional[int] = None
    reps_objetivo: Optional[str] = None
    notas: Optional[str] = None


class RutinaPlanDiaRequest(BaseModel):
    dia_semana: str
    ejercicios: list[RutinaPlanEjercicio]


# ---- Rutas chat ----

@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(os.path.join(_static_dir, "index.html"))


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.mensaje or not request.mensaje.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    chat_id = request.chat_id or str(uuid.uuid4())
    try:
        respuesta = await procesar_mensaje(request.mensaje.strip(), chat_id=chat_id)
        return ChatResponse(respuesta=respuesta, chat_id=chat_id)

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"Servicio temporalmente no disponible: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@app.get("/api/chat/historial")
async def get_chat_historial(limite: int = 30, chat_id: Optional[str] = None):
    try:
        from memory.conectar_sheets import leer_conversaciones
        return await leer_conversaciones(limite=limite, chat_id=chat_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/conversaciones")
async def get_chat_conversaciones():
    try:
        from memory.conectar_sheets import listar_conversaciones
        return await listar_conversaciones()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@app.get("/api/rutina/plan")
async def get_rutina_plan():
    try:
        from memory.lectura_estructurada import leer_rutina_plan
        return await leer_rutina_plan()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rutina/plan")
async def post_rutina_plan(request: RutinaPlanDiaRequest):
    try:
        from memory.lectura_estructurada import guardar_rutina_plan_dia, leer_rutina_plan
        await guardar_rutina_plan_dia(request.dia_semana, [e.dict() for e in request.ejercicios])
        return await leer_rutina_plan()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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


# ---- Endpoints Fase 1: biométricos, check-in, medidas, hidratación, dolor ----

@app.post("/api/biometricos")
async def post_biometricos(request: BiometricosRequest):
    """Guarda biométricos (manual desde la web o Watch/Android)."""
    try:
        from db.repositorio import guardar_biometricos
        datos = {k: v for k, v in request.model_dump().items() if v is not None}
        result = await asyncio.to_thread(guardar_biometricos, datos)
        return {"ok": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/biometricos/hoy")
async def get_biometricos_hoy():
    try:
        from db.repositorio import leer_biometricos_hoy
        data = await asyncio.to_thread(leer_biometricos_hoy)
        return data or {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/checkin")
async def post_checkin(request: CheckinRequest):
    try:
        from db.repositorio import guardar_checkin
        datos = {k: v for k, v in request.model_dump().items() if v is not None}
        result = await asyncio.to_thread(guardar_checkin, datos)
        return {"ok": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/checkin/hoy")
async def get_checkin_hoy():
    try:
        from db.repositorio import leer_checkin_hoy
        data = await asyncio.to_thread(leer_checkin_hoy)
        return data or {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/medidas")
async def post_medidas(request: MedidasRequest):
    try:
        from db.repositorio import guardar_medidas
        datos = {k: v for k, v in request.model_dump().items() if v is not None}
        result = await asyncio.to_thread(guardar_medidas, datos)
        return {"ok": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/medidas")
async def get_medidas():
    try:
        from db.repositorio import leer_medidas_recientes
        data = await asyncio.to_thread(leer_medidas_recientes)
        return {"medidas": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/hidratacion")
async def post_hidratacion(request: HidratacionRequest):
    try:
        from db.repositorio import guardar_hidratacion
        result = await asyncio.to_thread(guardar_hidratacion, request.litros, request.fecha)
        return {"ok": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dolor")
async def post_dolor(request: DolorRequest):
    try:
        from db.repositorio import registrar_dolor
        result = await asyncio.to_thread(
            registrar_dolor, request.zona, request.intensidad, request.notas or "", request.fecha
        )
        return {"ok": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dolor/activos")
async def get_dolores_activos():
    try:
        from db.repositorio import leer_dolores_activos
        data = await asyncio.to_thread(leer_dolores_activos)
        return {"dolores": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---- Endpoints Fase 5: plan nutricional con timing ----

@app.get("/api/nutricion/timing")
async def get_nutricion_timing(recalcular: bool = False):
    """
    Retorna el plan nutricional de hoy con timing por toma.
    Si no existe o recalcular=true, lo genera con el LLM.
    El LLM ancla las comidas a la hora de entrenamiento del día.
    """
    try:
        from db.repositorio import (
            leer_plan_nutricional_hoy, guardar_plan_nutricional,
            leer_cronotipo,
        )
        from engine.calcular_macros import (
            calcular_timing_nutricional, _extraer_hora_entreno_hoy,
        )
        from memory.lectura_estructurada import leer_nutricion_hoy, leer_perfil

        plan = None if recalcular else await asyncio.to_thread(leer_plan_nutricional_hoy)

        if not plan:
            # Leer macros objetivo + contexto del usuario en paralelo
            nutricion_hoy, perfil, cronotipo = await asyncio.gather(
                leer_nutricion_hoy(),
                leer_perfil(),
                asyncio.to_thread(leer_cronotipo),
                return_exceptions=True,
            )
            macros_obj = {}
            if not isinstance(nutricion_hoy, Exception):
                macros_obj = nutricion_hoy.get("objetivo") or {}
            if not macros_obj.get("kcal"):
                macros_obj = {"kcal": 2200, "proteinas_g": 160, "carbos_g": 240, "grasas_g": 75}

            # Extraer hora de entreno de hoy desde el perfil
            dias_txt = (perfil or {}).get("dias_tipicos", "") if not isinstance(perfil, Exception) else ""
            plan_txt = (perfil or {}).get("plan_semanal", "") if not isinstance(perfil, Exception) else ""
            hora_entreno = _extraer_hora_entreno_hoy(dias_txt or "", plan_txt or "")

            crono = cronotipo if isinstance(cronotipo, str) else None

            timing = await calcular_timing_nutricional(macros_obj, hora_entreno, crono)

            tomas = timing.get("tomas") or []
            notas = timing.get("notas") or ""
            await asyncio.to_thread(guardar_plan_nutricional, tomas, hora_entreno, notas)

            plan = {
                "fecha": timing.get("fecha"),
                "hora_entreno": hora_entreno,
                "tomas": tomas,
                "notas": notas,
            }

        return plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---- Catch-all para BrowserRouter (debe ir al final) ----

@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str):
    index = os.path.join(_static_dir, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="Not found")
