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
from engine.parsear_edicion_rutina import parsear_edicion_rutina
from rag.buscar_contexto import buscar_contexto


def _aplicar_edicion_rutina(ejercicios_actuales: list[dict], edicion: dict) -> list[dict]:
    """Aplica una edición (reemplazar/agregar/eliminar/vaciar_dia) sobre la lista de ejercicios de un día."""
    accion = edicion.get("accion")
    objetivo = (edicion.get("ejercicio_objetivo") or "").strip().lower()
    nuevo = edicion.get("ejercicio_nuevo")

    if accion == "vaciar_dia":
        return []

    if accion == "eliminar":
        return [ej for ej in ejercicios_actuales if ej.get("ejercicio", "").strip().lower() != objetivo]

    if accion == "agregar" and nuevo:
        return [*ejercicios_actuales, nuevo]

    if accion == "reemplazar" and nuevo:
        nueva_lista = []
        reemplazado = False
        for ej in ejercicios_actuales:
            if not reemplazado and ej.get("ejercicio", "").strip().lower() == objetivo:
                nueva_lista.append(nuevo)
                reemplazado = True
            else:
                nueva_lista.append(ej)
        if not reemplazado:
            nueva_lista.append(nuevo)
        return nueva_lista

    return ejercicios_actuales


async def _buscar_memoria_semantica(mensaje: str) -> str | None:
    """
    Búsqueda semántica en memoria Supabase. Solo entra lo relevante al mensaje actual.
    Fallback silencioso a None → pipeline usará memoria de Sheets.
    """
    try:
        from db.repositorio import buscar_memoria_semantica
        resultado = await asyncio.to_thread(buscar_memoria_semantica, mensaje)
        return resultado if resultado else None
    except Exception as e:
        print(f"[pipeline] Memoria semántica no disponible (fallback Sheets): {e}")
        return None


async def _guardar_memoria_con_fallback(entrada: dict) -> None:
    """Guarda memoria en Supabase (semántica) con fallback a Sheets."""
    try:
        from db.repositorio import guardar_memoria_semantica
        await asyncio.to_thread(guardar_memoria_semantica, entrada)
    except Exception as e:
        print(f"[pipeline] Fallback memoria a Sheets: {e}")
        await guardar_memoria(entrada)


async def _decay_memoria_combinado() -> None:
    """Ejecuta decay en Supabase + Sheets (durante migración)."""
    try:
        from db.repositorio import decay_memoria_supabase
        await asyncio.to_thread(decay_memoria_supabase)
    except Exception as e:
        print(f"[pipeline] Decay Supabase error (no crítico): {e}")
    await decay_memoria()


async def _leer_plan_nutricional() -> dict | None:
    """Lee el plan nutricional de hoy (ya generado) desde Supabase. No genera si no existe."""
    try:
        from db.repositorio import leer_plan_nutricional_hoy
        return await asyncio.to_thread(leer_plan_nutricional_hoy)
    except Exception as e:
        print(f"[pipeline] Plan nutricional no disponible (no crítico): {e}")
        return None


async def _leer_rutina_plan_ctx() -> dict | None:
    """Lee el plan de rutina semanal (objetivo) guardado por el usuario. Ground truth para el LLM."""
    try:
        from memory.lectura_estructurada import leer_rutina_plan
        plan = await leer_rutina_plan()
        dias = plan.get("dias") or {}
        return plan if any(dias.values()) else None
    except Exception as e:
        print(f"[pipeline] Plan de rutina no disponible (no crítico): {e}")
        return None


async def _leer_recuperacion_hoy() -> dict | None:
    """
    Lee check-in, biométricos y dolores activos de Supabase.
    Devuelve dict combinado o None si Supabase no está disponible.
    """
    try:
        from db.repositorio import leer_checkin_hoy, leer_biometricos_hoy, leer_dolores_activos
        checkin, biometricos, dolores = await asyncio.gather(
            asyncio.to_thread(leer_checkin_hoy),
            asyncio.to_thread(leer_biometricos_hoy),
            asyncio.to_thread(leer_dolores_activos),
            return_exceptions=True,
        )
        resultado: dict = {}
        if checkin and not isinstance(checkin, Exception):
            resultado.update({k: v for k, v in checkin.items() if v is not None})
        if biometricos and not isinstance(biometricos, Exception):
            # Campos objetivos del Watch complementan el checkin subjetivo
            for campo in ("sueno_horas", "fc_reposo", "hrv", "spo2", "pasos"):
                if biometricos.get(campo) is not None:
                    resultado[campo] = biometricos[campo]
        if dolores and not isinstance(dolores, Exception):
            resultado["dolores_activos"] = dolores
        return resultado if resultado else None
    except Exception as e:
        print(f"[pipeline] Recuperación Supabase no disponible (no crítico): {e}")
        return None


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
    es_editar_rutina = intencion.get("tipo") == "editar_rutina"

    tasks_lectura = [
        leer_sheets(intencion["sheets_necesarias"]),  # idx 0
        leer_conversaciones(limite=10),               # idx 1
        _leer_recuperacion_hoy(),                     # idx 2: checkin + biometricos + dolores
        _buscar_memoria_semantica(mensaje),           # idx 3: memoria relevante (Supabase)
        _leer_plan_nutricional(),                     # idx 4: timing nutricional de hoy
        _leer_rutina_plan_ctx(),                      # idx 5: plan de rutina semanal (ground truth)
    ]
    if es_registro_entreno:
        tasks_lectura.append(parsear_entreno(mensaje))           # idx 6
    elif es_registro_comida:
        tasks_lectura.append(parsear_comida(mensaje))            # idx 6
    elif es_editar_rutina:
        tasks_lectura.append(parsear_edicion_rutina(mensaje))    # idx 6

    resultados_lectura = await asyncio.gather(*tasks_lectura, return_exceptions=True)
    contexto_usuario = resultados_lectura[0] if not isinstance(resultados_lectura[0], Exception) else {}
    conversaciones = resultados_lectura[1] if not isinstance(resultados_lectura[1], Exception) else []
    recuperacion = resultados_lectura[2] if not isinstance(resultados_lectura[2], Exception) else None
    memoria_semantica = resultados_lectura[3] if not isinstance(resultados_lectura[3], Exception) else None

    # Memoria semántica sobreescribe la de Sheets si está disponible
    if memoria_semantica is not None:
        contexto_usuario["memory"] = memoria_semantica

    plan_nutricional = resultados_lectura[4] if not isinstance(resultados_lectura[4], Exception) else None
    rutina_plan = resultados_lectura[5] if not isinstance(resultados_lectura[5], Exception) else None

    datos_parse_raw = resultados_lectura[6] if (es_registro_entreno or es_registro_comida or es_editar_rutina) else None
    if isinstance(datos_parse_raw, Exception):
        print(f"[pipeline] Error parseando registro: {datos_parse_raw}")
        datos_parse_raw = None

    datos_entreno_raw  = datos_parse_raw if es_registro_entreno else None
    datos_comida_raw   = datos_parse_raw if es_registro_comida  else None
    datos_edicion_raw  = datos_parse_raw if es_editar_rutina    else None

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

    rutina_editada = None
    if datos_edicion_raw and rutina_plan:
        try:
            from memory.lectura_estructurada import guardar_rutina_plan_dia, DIAS_SEMANA
            dias_actuales = rutina_plan.get("dias") or {}
            cambios_aplicados = []
            for edicion in datos_edicion_raw.get("ediciones", []):
                dia = edicion.get("dia_semana")
                if dia not in DIAS_SEMANA:
                    continue
                actuales = dias_actuales.get(dia, [])
                nueva_lista = _aplicar_edicion_rutina(actuales, edicion)
                await guardar_rutina_plan_dia(dia, nueva_lista)
                dias_actuales[dia] = nueva_lista
                cambios_aplicados.append({
                    "dia_semana": dia,
                    "accion": edicion.get("accion"),
                    "ejercicio_objetivo": edicion.get("ejercicio_objetivo"),
                    "ejercicio_nuevo": edicion.get("ejercicio_nuevo"),
                    "resultado_dia": nueva_lista,
                })
            if cambios_aplicados:
                rutina_editada = {"cambios": cambios_aplicados}
                rutina_plan = {"dias": dias_actuales}
                print(f"[pipeline] Rutina editada: {len(cambios_aplicados)} cambio(s) guardado(s)")
        except Exception as e:
            print(f"[pipeline] Error editando rutina: {e}")

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
        recuperacion=recuperacion,
        plan_nutricional=plan_nutricional,
        rutina_plan=rutina_plan,
        rutina_editada=rutina_editada,
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
            guardar_fn=_guardar_memoria_con_fallback,
            memoria_existente=contexto_usuario.get("memory", ""),
        )
    )

    # 8. Decay de memoria en background (Supabase + Sheets durante migración)
    asyncio.create_task(_decay_memoria_combinado())

    return respuesta
