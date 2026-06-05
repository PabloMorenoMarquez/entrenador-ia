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
    leer_sheets,
    leer_conversaciones,
    guardar_conversacion,
    guardar_memoria,
    guardar_entreno,
    guardar_comida,
    guardar_macros_objetivo,
    decay_memoria,
)
from engine.analizar_entrenamiento import analizar_entrenamiento
from engine.parsear_entreno import parsear_entreno
from engine.parsear_comida import parsear_comida
from rag.buscar_contexto import buscar_contexto


async def procesar_mensaje(mensaje: str) -> str:
    """
    Punto de entrada principal del pipeline.
    Recibe el mensaje del usuario y devuelve la respuesta del coach.
    """

    # 1. Detectar intención
    # Determina qué módulos activar y qué datos leer
    intencion = await detectar_intencion(mensaje)

    # 2. Leer datos necesarios en paralelo
    # sheets + conversaciones + parse entreno/comida (si aplica) al mismo tiempo
    es_registro_entreno = intencion.get("tipo") == "registro_entreno"
    es_registro_comida  = intencion.get("tipo") == "registro_comida"
    es_recalcular_macros = intencion.get("tipo") == "recalcular_macros"

    tasks_lectura = [
        leer_sheets(intencion["sheets_necesarias"]),
        leer_conversaciones(limite=10),
    ]
    if es_registro_entreno:
        tasks_lectura.append(parsear_entreno(mensaje))
    elif es_registro_comida:
        tasks_lectura.append(parsear_comida(mensaje))

    resultados_lectura = await asyncio.gather(*tasks_lectura, return_exceptions=True)
    contexto_usuario = resultados_lectura[0] if not isinstance(resultados_lectura[0], Exception) else {}
    conversaciones = resultados_lectura[1] if not isinstance(resultados_lectura[1], Exception) else []

    datos_parse_raw = resultados_lectura[2] if (es_registro_entreno or es_registro_comida) else None
    if isinstance(datos_parse_raw, Exception):
        print(f"[pipeline] Error parseando registro: {datos_parse_raw}")
        datos_parse_raw = None

    datos_entreno_raw = datos_parse_raw if es_registro_entreno else None
    datos_comida_raw  = datos_parse_raw if es_registro_comida  else None

    # 2.5 Guardar registro si fue parseado correctamente
    entreno_registrado = None
    comida_registrada  = None

    if datos_entreno_raw:
        try:
            sesion_id = await guardar_entreno(datos_entreno_raw)
            entreno_registrado = {**datos_entreno_raw, "sesion_id": sesion_id}
            print(f"[pipeline] Entreno guardado: {sesion_id}, {len(datos_entreno_raw.get('ejercicios', []))} ejercicios")
        except Exception as e:
            print(f"[pipeline] Error guardando entreno: {e}")

    if datos_comida_raw:
        try:
            filas = await guardar_comida(datos_comida_raw)
            comida_registrada = {**datos_comida_raw, "filas_guardadas": filas}
            print(f"[pipeline] Comida guardada: {filas} alimento(s)")
        except Exception as e:
            print(f"[pipeline] Error guardando comida: {e}")

    # 2.6 Recalcular macros si fue solicitado
    macros_recalculados = None
    if es_recalcular_macros:
        try:
            from engine.calcular_macros import calcular_macros_objetivo
            from memory.lectura_estructurada import leer_perfil
            perfil = await leer_perfil()
            macros_recalculados = await calcular_macros_objetivo(perfil)
            await guardar_macros_objetivo("dia", macros_recalculados)
            print(f"[pipeline] Macros recalculados: {macros_recalculados.get('kcal')} kcal")
        except Exception as e:
            print(f"[pipeline] Error recalculando macros: {e}")

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
        entreno_registrado=entreno_registrado,
        comida_registrada=comida_registrada,
        macros_recalculados=macros_recalculados,
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
            memoria_existente=contexto_usuario.get("memory", ""),
        )
    )

    # 8. Decay de memoria en background (expira entradas antiguas/baja prioridad)
    asyncio.create_task(decay_memoria())

    return respuesta
