"""
Construye el prompt dinámico para el LLM principal.
Solo incluye los bloques de contexto que son relevantes para la petición actual.
El conocimiento técnico NO va aquí — viene del RAG cuando se necesita.
"""

from typing import Optional

# Sistema base: corto y directo
# Sin conocimiento hardcodeado — para eso está el RAG
SISTEMA_BASE = """Eres Coach IA, entrenador personal y nutricionista deportivo. \
Respondes en español con precisión técnica y tono profesional.

Reglas:
- Si no tienes un dato necesario para una recomendación precisa, pregunta. Nunca inventes.
- Si usas una estimación, indícalo: "Estimación basada en [criterio]:".
- Máximo 1-2 preguntas por mensaje cuando las necesites.
- Cuando tengas suficiente información, actúa directamente sin preámbulos.
- No uses emojis excesivos ni frases motivacionales vacías.
- Si el contexto incluye "Entrenamiento que acaba de registrar" o "Comida que acaba de registrar", confirma explícitamente al inicio que ha quedado guardado antes de dar feedback."""


def construir_prompt(
    contexto_usuario: dict,
    mensaje: str,
    conversaciones: list[dict],
    motor_output: Optional[dict] = None,
    rag_context: Optional[str] = None,
    entreno_registrado: Optional[dict] = None,
    comida_registrada: Optional[dict] = None,
    macros_recalculados: Optional[dict] = None,
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

    # --- Entreno recién registrado (registro_entreno) ---
    if entreno_registrado:
        texto = _formatear_entreno_registrado(entreno_registrado)
        if texto:
            bloques.append(f"## Entrenamiento que acaba de registrar el usuario\n{texto}")

    # --- Comida recién registrada (registro_comida) ---
    if comida_registrada:
        texto = _formatear_comida_registrada(comida_registrada)
        if texto:
            bloques.append(f"## Comida que acaba de registrar el usuario\n{texto}")

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

    # --- Análisis del motor (solo si se ejecutó) ---
    if motor_output:
        texto_motor = _formatear_motor(motor_output)
        if texto_motor:
            bloques.append(f"## Análisis de entrenamiento\n{texto_motor}")

    # --- Contexto científico del RAG (solo si se consultó) ---
    if rag_context and rag_context.strip():
        bloques.append(f"## Evidencia científica relevante\n{rag_context}")

    # Construir mensaje del sistema
    sistema = SISTEMA_BASE
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

    return "\n".join(partes)
