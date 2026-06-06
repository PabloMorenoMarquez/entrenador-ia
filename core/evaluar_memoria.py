"""
Evalúa si la conversación contiene información relevante para guardar en memoria.
Se ejecuta de forma asíncrona DESPUÉS de devolver la respuesta al usuario.
No bloquea la respuesta.
"""

import json
import re
from typing import Callable, Awaitable
from core.llm import llamar_llm, MODELOS_MEMORIA

PROMPT_SISTEMA = """Analiza este intercambio entre un usuario y su coach IA.
Decide si contiene información que vale la pena guardar en la memoria del usuario.

Información que SÍ vale guardar:
- Datos personales nuevos o actualizados (peso, altura, edad)
- Objetivos nuevos o cambios de objetivo
- Limitaciones físicas o lesiones
- Preferencias o aversiones relevantes
- Progresos importantes (récord en un ejercicio, pérdida de peso, etc.)
- Información médica relevante

Información que NO vale guardar:
- Saludos o conversación trivial
- Preguntas genéricas ya respondidas
- Información que ya está en el perfil del usuario
- Información que YA está en la memoria existente (ver sección MEMORIA ACTUAL)

Responde SOLO con JSON válido, sin texto adicional, sin markdown:
{
  "guardar": true o false,
  "tipo": "perfil|objetivo|limitacion|preferencia|progreso|medico|null",
  "contenido": "resumen conciso en una frase de lo que guardar, o null",
  "prioridad": 1,2,3,4 o 5
}

Prioridad: 5=crítico (lesión grave, cambio de objetivo), 3=importante (progreso, preferencia clave), 1=menor"""


def _extraer_json(texto: str) -> dict:
    texto = texto.strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', texto)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    match = re.search(r'\{[\s\S]*\}', texto)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(texto.replace("'", '"'))
    except json.JSONDecodeError:
        pass
    raise ValueError(f"No se pudo extraer JSON de: {texto[:200]}")


async def evaluar_y_guardar_memoria(
    mensaje_usuario: str,
    respuesta_coach: str,
    guardar_fn: Callable[[dict], Awaitable[None]],
    memoria_existente: str = "",
) -> None:
    """
    Evalúa si la conversación merece guardarse en memoria.
    Si sí, llama a guardar_fn con el dict de memoria.

    Esta función se llama con asyncio.create_task() — no bloquea la respuesta.

    Args:
        mensaje_usuario: mensaje del usuario en este turno.
        respuesta_coach: respuesta generada por el LLM.
        guardar_fn: función async que guarda un dict en la sheet de memory.
        memoria_existente: texto con entradas actuales de memoria (para deduplicar).
    """
    try:
        conversacion = f"Usuario: {mensaje_usuario}\nCoach: {respuesta_coach}"
        if memoria_existente and memoria_existente.strip():
            conversacion += f"\n\n--- MEMORIA ACTUAL ---\n{memoria_existente.strip()}"

        respuesta = await llamar_llm(
            mensajes=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": conversacion},
            ],
            modelos=MODELOS_MEMORIA,
            max_tokens=150,
            response_format={"type": "json_object"},
        )

        resultado = _extraer_json(respuesta)

        if resultado.get("guardar") and resultado.get("contenido"):
            await guardar_fn({
                "tipo": resultado.get("tipo", "general"),
                "contenido": resultado["contenido"],
                "prioridad": resultado.get("prioridad", 3),
            })
            print(f"[memoria] Guardado: {resultado['contenido'][:60]}...")

    except Exception as e:
        # Error silencioso — la memoria es best-effort, no crítica
        print(f"[evaluar_memoria] Error (no crítico): {e}")