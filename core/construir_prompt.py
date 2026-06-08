"""
Construye el prompt dinámico para el LLM principal.
Solo incluye los bloques de contexto que son relevantes para la petición actual.
El conocimiento técnico NO va aquí — viene del RAG cuando se necesita.
"""

import re
from typing import Optional

_REGLAS_FIJAS = """Reglas:
- Si no tienes un dato necesario para una recomendación precisa, pregunta. Nunca inventes.
- Si usas una estimación, indícalo: "Estimación basada en [criterio]:".
- Máximo 1-2 preguntas por mensaje cuando las necesites.
- Cuando tengas suficiente información, actúa directamente sin preámbulos.
- Si el usuario te pide explícitamente que decidas tú ("tú decides", "tú eres el experto", "haz lo que veas mejor"), da UNA única recomendación concreta y directa. No enumeres "Opción A / Opción B" ni listes ventajas y desventajas de cada una — eso es justo lo que el usuario te ha pedido que evites. Puedes mencionar en una frase breve por qué eliges esa opción, pero la respuesta debe cerrar con una decisión clara, no con la pelota de vuelta en su tejado.
- No valides por defecto cada idea del usuario. Si algo que propone es razonable pero hay una opción mejor, dilo directamente y explica por qué — el usuario prefiere ese debate a que le des siempre la razón. Reserva el acuerdo simple para cuando de verdad no haya nada que mejorar.
- No uses emojis excesivos ni frases motivacionales vacías.
- Si el contexto incluye "Entrenamiento que acaba de registrar", "Comida que acaba de registrar" o "Cambios aplicados a la rutina", confirma explícitamente al inicio que ha quedado guardado antes de dar feedback."""


def _extraer_campo(texto: str, *patrones: str) -> str:
    """Extrae el valor de un campo clave:valor del texto de perfil."""
    patron_combinado = "|".join(patrones)
    match = re.search(
        rf'(?:^|\n)\s*(?:{patron_combinado})\s*[:\|]\s*(.+?)(?:\n|$)',
        texto,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else ""


def _extraer_limitaciones(memoria_txt: str) -> str:
    """Extrae limitaciones físicas activas de la memoria del usuario."""
    if not memoria_txt:
        return ""
    limitaciones = []
    for linea in memoria_txt.split("\n"):
        linea_lower = linea.lower()
        if any(kw in linea_lower for kw in [
            "limitacion", "limitación", "lesion", "lesión",
            "dolor", "medico", "médico", "no puede", "evitar",
        ]):
            # Intentar extraer el campo contenido de la línea formateada
            m = re.search(r'contenido[:\s]+(.+?)(?:\s*[\|,]|\s*prioridad|$)', linea, re.IGNORECASE)
            fragmento = m.group(1).strip() if m else linea.strip()
            if fragmento and len(fragmento) < 200:
                limitaciones.append(fragmento)
    return "; ".join(limitaciones[:3])


def construir_sistema(
    contexto_usuario: dict,
    motor_output: Optional[dict] = None,
    recuperacion: Optional[dict] = None,
) -> str:
    """
    Construye un system prompt personalizado para este atleta concreto.
    Inyecta nombre, nivel, limitaciones activas y estado de recuperación como directivas.
    """
    perfil_txt = contexto_usuario.get("perfil_usuario", "")
    memoria_txt = contexto_usuario.get("memory", "")

    nombre = _extraer_campo(perfil_txt, "nombre", "name")
    nivel = _extraer_campo(perfil_txt, "nivel", "level", "nivel_entrenamiento")
    objetivo_perfil = _extraer_campo(perfil_txt, "objetivo_principal", "objetivo")

    lesiones = _extraer_limitaciones(memoria_txt)

    # --- Introducción personalizada ---
    intro_partes = ["Eres Coach IA, entrenador personal y nutricionista deportivo."]
    if nombre:
        intro_partes.append(f"Tu atleta se llama {nombre}.")
    if nivel:
        intro_partes.append(f"Nivel de entrenamiento: {nivel}.")
    if objetivo_perfil:
        intro_partes.append(f"Objetivo principal: {objetivo_perfil}.")
    intro_partes.append("Respondes en español con precisión técnica y tono profesional.")
    intro = " ".join(intro_partes)

    # --- Directivas críticas ---
    directivas = []

    if lesiones:
        directivas.append(
            f"LIMITACIONES ACTIVAS: {lesiones}. "
            "Nunca prescribas el movimiento doloroso. Antes de ofrecer una alternativa, "
            "comprueba explícitamente que NO comparte el mismo patrón de movimiento ni "
            "carga la misma zona afectada (ej.: si hay problema de coxis/lumbar, descarta "
            "también ejercicios de bisagra de cadera, no solo el movimiento original). "
            "Si dudas si una variante es segura, dilo y pregunta antes de prescribirla."
        )

    # Check-in de recuperación (Fase 1+)
    if recuperacion:
        fatiga = recuperacion.get("fatiga")
        sueno = recuperacion.get("calidad_sueno")
        dolor = recuperacion.get("dolor_muscular")
        estado_mental = recuperacion.get("estado_mental")
        partes_rec = []
        if fatiga is not None:
            partes_rec.append(f"fatiga {fatiga}/5")
        if sueno is not None:
            partes_rec.append(f"sueño {sueno}/5")
        if dolor is not None:
            partes_rec.append(f"dolor muscular {dolor}/5")
        if estado_mental is not None:
            partes_rec.append(f"estado mental {estado_mental}/5")
        if partes_rec:
            resumen_rec = ", ".join(partes_rec)
            if fatiga is not None and fatiga <= 2:
                directivas.append(
                    f"RECUPERACIÓN HOY: {resumen_rec}. "
                    "Atleta fatigado. Modera intensidad y volumen. No fuerces progresión."
                )
            elif fatiga is not None and fatiga >= 4:
                directivas.append(
                    f"RECUPERACIÓN HOY: {resumen_rec}. "
                    "Atleta bien recuperado. Puedes proponer sesión de alta intensidad."
                )
            else:
                directivas.append(f"RECUPERACIÓN HOY: {resumen_rec}.")

    # Estado global del motor de entrenamiento + periodización
    if motor_output:
        estado_g = motor_output.get("estado_global") or {}
        score = estado_g.get("score_global", 50)
        estado = estado_g.get("estado", "")
        if score < 40:
            directivas.append(
                f"ANÁLISIS MOTOR: atleta en estado {estado.upper()} "
                f"(score {score}/100). Prioriza recuperación. No escales carga hoy."
            )
        elif score < 60:
            directivas.append(
                f"ANÁLISIS MOTOR: {estado} (score {score}/100). "
                "Mantén cargas conservadoras."
            )

        # Directiva de fase del mesociclo
        peri = motor_output.get("periodizacion") or {}
        fase = peri.get("fase")
        if fase:
            from engine.motor_decision import UMBRALES
            if fase == "deload":
                directivas.append(
                    "FASE DELOAD activa: reduce volumen al 50%, mantén intensidad moderada. "
                    "No persig progresión esta semana."
                )
            elif fase == "fuerza":
                rir_obj = UMBRALES.get("fuerza", {}).get("rir_optimo", 3)
                directivas.append(
                    f"FASE FUERZA: prioriza cargas altas (RIR objetivo {rir_obj}), "
                    "volumen bajo (6-10 series/grupo). Progresión de carga > volumen."
                )
            elif fase == "hipertrofia":
                rir_obj = UMBRALES.get("hipertrofia", {}).get("rir_optimo", 2)
                directivas.append(
                    f"FASE HIPERTROFIA: volumen moderado-alto (14-20 series/grupo), "
                    f"RIR objetivo {rir_obj}. Progresión progresiva semana a semana."
                )

    # Ensamblar sistema
    bloques = [intro]
    if directivas:
        bloques.append("\n".join(directivas))
    bloques.append(_REGLAS_FIJAS)
    return "\n\n".join(bloques)


def construir_prompt(
    contexto_usuario: dict,
    mensaje: str,
    conversaciones: list[dict],
    motor_output: Optional[dict] = None,
    rag_context: Optional[str] = None,
    entreno_registrado: Optional[dict] = None,
    comida_registrada: Optional[dict] = None,
    macros_recalculados: Optional[dict] = None,
    recuperacion: Optional[dict] = None,
    plan_nutricional: Optional[dict] = None,
    rutina_plan: Optional[dict] = None,
    rutina_editada: Optional[dict] = None,
) -> list[dict]:
    """
    Ensambla los mensajes para la llamada al LLM.

    Args:
        contexto_usuario: dict con los datos de las sheets leídas.
                          Claves posibles: perfil_usuario, objetivos, plan_semanal,
                          dias_tipicos, alimentos_disponibles, memory.
        mensaje: mensaje actual del usuario.
        conversaciones: lista de dicts con keys 'rol' y 'contenido'.
        motor_output: dict del motor de entrenamiento (puede ser None).
        rag_context: string con contexto científico del RAG (puede ser None).

    Returns:
        Lista de mensajes en formato OpenRouter/OpenAI.
    """
    bloques = []

    # --- Contexto del usuario ---
    if contexto_usuario.get("perfil_usuario"):
        bloques.append(f"## Perfil\n{contexto_usuario['perfil_usuario']}")

    if contexto_usuario.get("objetivos"):
        bloques.append(f"## Objetivo actual\n{contexto_usuario['objetivos']}")

    if contexto_usuario.get("plan_semanal"):
        bloques.append(f"## Plan semanal\n{contexto_usuario['plan_semanal']}")

    if contexto_usuario.get("dias_tipicos"):
        bloques.append(f"## Días de entrenamiento\n{contexto_usuario['dias_tipicos']}")

    if contexto_usuario.get("alimentos_disponibles"):
        bloques.append(f"## Alimentos disponibles\n{contexto_usuario['alimentos_disponibles']}")

    if contexto_usuario.get("memory"):
        bloques.append(f"## Lo que recuerdo del usuario\n{contexto_usuario['memory']}")

    # --- Estado de recuperación hoy (check-in + biométricos + dolores) ---
    if recuperacion:
        lineas_rec = []
        if recuperacion.get("fatiga") is not None:
            lineas_rec.append(f"Fatiga: {recuperacion['fatiga']}/5")
        if recuperacion.get("dolor_muscular") is not None:
            lineas_rec.append(f"Dolor muscular: {recuperacion['dolor_muscular']}/5")
        if recuperacion.get("calidad_sueno") is not None:
            lineas_rec.append(f"Calidad sueño: {recuperacion['calidad_sueno']}/5")
        if recuperacion.get("estado_mental") is not None:
            lineas_rec.append(f"Estado mental: {recuperacion['estado_mental']}/5")
        if recuperacion.get("sueno_horas") is not None:
            lineas_rec.append(f"Horas de sueño: {recuperacion['sueno_horas']}h")
        if recuperacion.get("hrv") is not None:
            lineas_rec.append(f"HRV: {recuperacion['hrv']}ms")
        if recuperacion.get("fc_reposo") is not None:
            lineas_rec.append(f"FC reposo: {recuperacion['fc_reposo']}bpm")
        if recuperacion.get("pasos") is not None:
            lineas_rec.append(f"Pasos ayer: {recuperacion['pasos']}")
        dolores = recuperacion.get("dolores_activos") or []
        if dolores:
            zonas = ", ".join(f"{d['zona']} {d['intensidad']}/10" for d in dolores)
            lineas_rec.append(f"Dolores activos: {zonas}")
        if lineas_rec:
            bloques.append(f"## Estado de recuperación hoy\n" + "\n".join(lineas_rec))

    # --- Entreno recién registrado (registro_entreno) ---
    if entreno_registrado:
        texto = _formatear_entreno_registrado(entreno_registrado)
        if texto:
            bloques.append(f"## Entrenamiento que acaba de registrar el usuario\n{texto}")

    # --- Comida recién registrada (registro_comida) ---
    if comida_registrada:
        texto = _formatear_comida_registrada(comida_registrada)
        if texto:
            bloques.append(
                "## Comida que acaba de registrar el usuario (fuente de verdad)\n"
                "Estos son los alimentos y macros YA calculados y guardados en su registro de hoy. "
                "Cuando confirmes el registro o resumas lo que ha comido, USA ESTOS VALORES tal cual — "
                "no recalcules ni estimes tus propias cifras de proteína/kcal/carbos/grasas a partir de "
                "tu conocimiento general de los alimentos, generarías un número distinto al guardado.\n"
                + texto
            )

    # --- Macros recalculados por LLM ---
    if macros_recalculados:
        kcal = macros_recalculados.get("kcal", "")
        p = macros_recalculados.get("proteinas_g", "")
        c = macros_recalculados.get("carbos_g", "")
        g = macros_recalculados.get("grasas_g", "")
        notas = macros_recalculados.get("notas", "")
        texto = f"Nuevos macros objetivo diarios calculados y guardados: {kcal} kcal, {p}g proteína, {c}g carbos, {g}g grasa."
        if notas:
            texto += f" {notas}"
        bloques.append(f"## Macros objetivo recalculados\n{texto}")

    # --- Plan de rutina semanal guardado (ground truth, evita confabulación) ---
    if rutina_plan:
        texto_rutina_plan = _formatear_rutina_plan(rutina_plan)
        if texto_rutina_plan:
            bloques.append(
                "## Rutina semanal guardada por el usuario (fuente de verdad)\n"
                "Esta es la rutina EXACTA que el usuario tiene guardada ahora mismo (ya incluye "
                "cualquier cambio aplicado en este mismo turno). Si te pregunta qué rutina tiene o "
                "le pides que la recuerdes, usa SOLO esto — no inventes ni reconstruyas de memoria.\n"
                "Sobre ediciones: el sistema SÍ puede guardar cambios de rutina automáticamente "
                "cuando el usuario pide explícitamente cambiar/añadir/quitar un ejercicio o vaciar "
                "un día. Si ves más abajo un bloque 'Cambios aplicados a la rutina', esos cambios YA "
                "están guardados — confírmalo sin rodeos, sin decir que lo va a tener que hacer él. "
                "Si el usuario pide un cambio y NO aparece ese bloque, el sistema no ha podido "
                "aplicarlo (mensaje ambiguo, día/ejercicio no identificado, etc.) — en ese caso NO "
                "digas que ya está guardado; pídele que lo reformule indicando el día y el ejercicio "
                "exacto, o que lo edite directamente en la vista Rutina de la app.\n"
                + texto_rutina_plan
            )

    # --- Cambios de rutina aplicados en este turno (editar_rutina) ---
    if rutina_editada:
        texto_edicion = _formatear_rutina_editada(rutina_editada)
        if texto_edicion:
            bloques.append(
                "## Cambios aplicados a la rutina (fuente de verdad — ya guardados)\n"
                "Estos cambios se acaban de guardar en la base de datos del usuario. Confirma "
                "explícitamente al inicio de tu respuesta qué se ha cambiado — usa estos datos tal "
                "cual, no los reformules de memoria — y luego da tu opinión o feedback si procede.\n"
                + texto_edicion
            )

    # --- Plan nutricional con timing (Fase 5) ---
    if plan_nutricional:
        tomas = plan_nutricional.get("tomas") or []
        hora_entreno = plan_nutricional.get("hora_entreno") or ""
        notas_plan = plan_nutricional.get("notas") or ""
        if tomas:
            lineas_plan = []
            if hora_entreno:
                lineas_plan.append(f"Entreno hoy: {hora_entreno}")
            for t in tomas:
                nombre = t.get("nombre", "Toma")
                hora = t.get("hora", "")
                proposito = t.get("proposito", "")
                kcal_t = t.get("kcal", "")
                p_t = t.get("proteinas_g", "")
                c_t = t.get("carbos_g", "")
                g_t = t.get("grasas_g", "")
                ejemplos = t.get("ejemplos") or []
                tag = f" [{proposito}]" if proposito else ""
                macros_str = f"{kcal_t}kcal | P{p_t}g C{c_t}g G{g_t}g"
                lineas_plan.append(f"{hora} {nombre}{tag}: {macros_str}")
                if ejemplos:
                    lineas_plan.append(f"  Ej: {', '.join(ejemplos[:2])}")
            if notas_plan:
                lineas_plan.append(f"Nota: {notas_plan}")
            bloques.append(
                "## Plan nutricional de hoy (fuente de verdad)\n"
                "Estos son los horarios y macros de comida que el usuario YA tiene guardados/calculados "
                "para hoy. Si te pregunta por horarios de comidas, ritmos circadianos o cómo organizar "
                "su día, USA ESTO como base — no inventes horarios nuevos desde cero ni ignores este "
                "plan. Si propones ajustes, parte de estos horarios y justifica el cambio explícitamente.\n"
                + "\n".join(lineas_plan)
            )

    # --- Análisis del motor (solo si se ejecutó) ---
    if motor_output:
        texto_motor = _formatear_motor(motor_output)
        if texto_motor:
            bloques.append(f"## Análisis de entrenamiento\n{texto_motor}")

        # Periodización: fase actual, objetivo de volumen, estancados
        peri = motor_output.get("periodizacion") or {}
        resumen_peri = peri.get("resumen_texto", "")
        if resumen_peri:
            bloques.append(f"## Plan de entrenamiento (mesociclo)\n{resumen_peri}")

    # --- Contexto científico del RAG (solo si se consultó) ---
    if rag_context and rag_context.strip():
        bloques.append(f"## Evidencia científica relevante\n{rag_context}")

    # Construir mensaje del sistema personalizado
    sistema = construir_sistema(contexto_usuario, motor_output, recuperacion)
    if bloques:
        sistema += "\n\n" + "\n\n".join(bloques)

    # --- Armar lista de mensajes ---
    mensajes = [{"role": "system", "content": sistema}]

    # Historial de conversación (últimos 10 turnos)
    for turno in conversaciones[-10:]:
        rol = turno.get("rol", "user")
        contenido = turno.get("contenido", "")
        if rol in ("user", "assistant") and contenido:
            mensajes.append({"role": rol, "content": contenido})

    # Mensaje actual
    mensajes.append({"role": "user", "content": mensaje})

    return mensajes


def _formatear_entreno_registrado(datos: dict) -> str:
    """Formatea el entreno recién guardado para incluirlo en el prompt."""
    partes = []
    sesion_id = datos.get("sesion_id", "")
    if sesion_id:
        partes.append(f"Sesion ID: {sesion_id}")
    sesion = datos.get("sesion") or {}
    if sesion.get("tipo_sesion"):
        partes.append(f"Tipo: {sesion['tipo_sesion']}")
    ejercicios = datos.get("ejercicios") or []
    for ej in ejercicios:
        nombre = ej.get("ejercicio", "")
        series = ej.get("series")
        reps = ej.get("reps_realizadas") or ej.get("reps_objetivo")
        peso = ej.get("peso_kg")
        rir = ej.get("rir")
        linea = nombre
        if series and reps:
            linea += f" {series}x{reps}"
        if peso:
            linea += f" {peso}kg"
        if rir is not None:
            linea += f" RIR{rir}"
        if linea:
            partes.append(f"- {linea}")
    return "\n".join(partes)


def _formatear_comida_registrada(datos: dict) -> str:
    """Formatea la comida recién guardada para incluirla en el prompt."""
    partes = []
    comida = datos.get("comida") or {}
    if comida.get("tipo_comida"):
        partes.append(f"Tipo: {comida['tipo_comida']}")
    alimentos = datos.get("alimentos") or []
    for al in alimentos:
        nombre = al.get("alimento", "")
        cantidad = al.get("cantidad_g_ml")
        kcal = al.get("calorias")
        prot = al.get("proteinas_g")
        carbos = al.get("carbos_g")
        grasas = al.get("grasas_g")
        linea = nombre
        if cantidad:
            linea += f" {cantidad}g"
        macros = []
        if kcal:
            macros.append(f"{kcal}kcal")
        if prot:
            macros.append(f"P{prot}g")
        if carbos:
            macros.append(f"C{carbos}g")
        if grasas:
            macros.append(f"G{grasas}g")
        if macros:
            linea += f" ({', '.join(macros)})"
        if linea:
            partes.append(f"- {linea}")
    filas_guardadas = datos.get("filas_guardadas")
    if filas_guardadas:
        partes.append(f"Guardado: {filas_guardadas} alimento(s) en registro_comidas")
    return "\n".join(partes)


_DIAS_LABEL = {
    "lunes": "Lunes", "martes": "Martes", "miercoles": "Miércoles",
    "jueves": "Jueves", "viernes": "Viernes", "sabado": "Sábado", "domingo": "Domingo",
}


def _formatear_rutina_plan(rutina_plan: dict) -> str:
    """Formatea el plan de rutina semanal guardado (objetivo por día) para el prompt."""
    dias = rutina_plan.get("dias") or {}
    partes = []
    for dia_key, label in _DIAS_LABEL.items():
        ejercicios = dias.get(dia_key) or []
        if not ejercicios:
            continue
        partes.append(f"{label}:")
        for ej in ejercicios:
            nombre = ej.get("ejercicio", "")
            series = ej.get("series_objetivo")
            reps = ej.get("reps_objetivo")
            grupo = ej.get("grupo_muscular")
            linea = f"  - {nombre}"
            if series and reps:
                linea += f": {series}x{reps}"
            elif reps:
                linea += f": {reps}"
            if grupo:
                linea += f" ({grupo})"
            partes.append(linea)
    return "\n".join(partes)


def _formatear_rutina_editada(datos: dict) -> str:
    """Formatea los cambios de rutina recién guardados (editar_rutina) para el prompt."""
    partes = []
    for cambio in datos.get("cambios") or []:
        dia = _DIAS_LABEL.get(cambio.get("dia_semana"), cambio.get("dia_semana", ""))
        accion = cambio.get("accion")
        objetivo = cambio.get("ejercicio_objetivo")
        nuevo = cambio.get("ejercicio_nuevo") or {}
        nombre_nuevo = nuevo.get("ejercicio")

        if accion == "reemplazar" and objetivo and nombre_nuevo:
            linea = f"{dia}: {objetivo} → {nombre_nuevo}"
        elif accion == "agregar" and nombre_nuevo:
            linea = f"{dia}: añadido {nombre_nuevo}"
        elif accion == "eliminar" and objetivo:
            linea = f"{dia}: eliminado {objetivo}"
        elif accion == "vaciar_dia":
            linea = f"{dia}: día vaciado (sin ejercicios)"
        else:
            continue

        if nombre_nuevo:
            series = nuevo.get("series_objetivo")
            reps = nuevo.get("reps_objetivo")
            if series and reps:
                linea += f" ({series}x{reps})"
            elif reps:
                linea += f" ({reps})"
        partes.append(f"- {linea}")
    return "\n".join(partes)


def _formatear_motor(motor_output: dict) -> str:
    """
    Convierte el dict del motor en texto legible para el LLM.
    Formato esperado del motor:
    {
        "objetivo": str,
        "ejercicios": dict,
        "alertas_sesion": list,
        "alertas_volumen": list,
        "volumen_semanal": dict,
        "resumen": list
    }
    """
    partes = []

    if motor_output.get("objetivo"):
        partes.append(f"Objetivo: {motor_output['objetivo']}")

    if motor_output.get("resumen"):
        resumen = motor_output["resumen"]
        if isinstance(resumen, list):
            partes.append("Resumen: " + " | ".join(str(r) for r in resumen))
        else:
            partes.append(f"Resumen: {resumen}")

    if motor_output.get("alertas_sesion"):
        alertas = motor_output["alertas_sesion"]
        if isinstance(alertas, list) and alertas:
            partes.append("Alertas de sesión: " + " | ".join(str(a) for a in alertas))

    if motor_output.get("alertas_volumen"):
        alertas = motor_output["alertas_volumen"]
        if isinstance(alertas, list) and alertas:
            partes.append("Alertas de volumen: " + " | ".join(str(a) for a in alertas))

    if motor_output.get("volumen_semanal"):
        vol = motor_output["volumen_semanal"]
        if isinstance(vol, dict) and vol:
            resumen_vol = ", ".join(f"{k}: {v}" for k, v in vol.items())
            partes.append(f"Volumen semanal: {resumen_vol}")

    if motor_output.get("estado_global"):
        eg = motor_output["estado_global"]
        if isinstance(eg, dict):
            score = eg.get("score_global", "")
            estado = eg.get("estado", "")
            desglose = eg.get("desglose", {})
            partes.append(f"Estado global: {estado} (score {score}/100)")
            if isinstance(desglose, dict) and desglose:
                detalle = ", ".join(f"{k}: {v}" for k, v in desglose.items())
                partes.append(f"Desglose: {detalle}")

    return "\n".join(partes)
