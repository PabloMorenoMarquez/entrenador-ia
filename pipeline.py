"""
Pipeline principal del entrenador IA.
Orquesta todos los módulos para procesar un mensaje del usuario.

Flujo:
1. Detectar intención
2. Leer sheets necesarias + conversaciones (en paralelo)
3. Ejecutar motor y/o RAG (en paralelo, solo si se necesitan)
4. Construir prompt dinámico
5. Llamar al LLM principal
6. Guardar conversación
7. Evaluar memoria en background (no bloquea)
"""

import asyncio

from core.llm import llamar_llm, MODELOS_PRINCIPAL
from core.detectar_intencion import detectar_intencion
from core.construir_prompt import construir_prompt
from core.evaluar_memoria import evaluar_y_guardar_memoria

# --- Interfaces esperadas de los módulos existentes ---
# Estos imports asumen la nueva estructura de carpetas.
# Si los archivos aún están en la raíz, ajusta las rutas.
from memory.conectar_sheets import (
    leer_sheets,          # async def leer_sheets(nombres: list[str]) -> dict
    leer_conversaciones,  # async def leer_conversaciones(limite: int) -> list[dict]
    guardar_conversacion, # async def guardar_conversacion(mensaje_usuario: str, respuesta_coach: str) -> None
    guardar_memoria,      # async def guardar_memoria(entrada: dict) -> None
)
from engine.analizar_entrenamiento import analizar_entrenamiento  # sync, devuelve dict informe
from rag.buscar_contexto import buscar_contexto                    # sync, devuelve str


async def procesar_mensaje(mensaje: str) -> str:
    """
    Punto de entrada principal del pipeline.
    Recibe el mensaje del usuario y devuelve la respuesta del coach.
    """

    # 1. Detectar intención
    # Determina qué módulos activar y qué datos leer
    intencion = await detectar_intencion(mensaje)

    # 2. Leer datos necesarios en paralelo
    # sheets + conversaciones al mismo tiempo para reducir latencia
    contexto_usuario, conversaciones = await asyncio.gather(
        leer_sheets(intencion["sheets_necesarias"]),
        leer_conversaciones(limite=10),
    )

    # 3. Motor y RAG en paralelo (solo si los necesitamos)
    motor_output = None
    rag_context = None

    tareas = {}
    if intencion.get("necesita_motor"):
        tareas["motor"] = asyncio.to_thread(analizar_entrenamiento, contexto_usuario)
    if intencion.get("necesita_rag"):
        tareas["rag"] = asyncio.to_thread(buscar_contexto, mensaje)

    if tareas:
        claves = list(tareas.keys())
        resultados = await asyncio.gather(*tareas.values(), return_exceptions=True)

        for clave, resultado in zip(claves, resultados):
            if isinstance(resultado, Exception):
                print(f"[pipeline] Error en {clave}: {resultado}")
                continue
            if clave == "motor":
                motor_output = resultado
            elif clave == "rag":
                rag_context = resultado

    # 4. Construir prompt dinámico
    mensajes = construir_prompt(
        contexto_usuario=contexto_usuario,
        mensaje=mensaje,
        conversaciones=conversaciones,
        motor_output=motor_output,
        rag_context=rag_context,
    )

    # 5. Llamar al LLM principal con fallback automático
    respuesta = await llamar_llm(
        mensajes=mensajes,
        modelos=MODELOS_PRINCIPAL,
        max_tokens=1000,
    )

    # 6. Guardar conversación (bloqueante — debe ocurrir antes de responder)
    await guardar_conversacion(
        mensaje_usuario=mensaje,
        respuesta_coach=respuesta,
    )

    # 7. Evaluar si guardar algo en memoria (no bloquea la respuesta)
    asyncio.create_task(
        evaluar_y_guardar_memoria(
            mensaje_usuario=mensaje,
            respuesta_coach=respuesta,
            guardar_fn=guardar_memoria,
        )
    )

    return respuesta
