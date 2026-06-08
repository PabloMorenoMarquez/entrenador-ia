"""
Parsea mensajes de edición de rutina semanal en datos estructurados.
LLM extrae qué día(s), qué acción (reemplazar/agregar/eliminar/vaciar) y qué ejercicio de texto libre.
"""

import json
import re
from core.llm import llamar_llm, MODELOS_INTENCION

PROMPT_SISTEMA = """Eres un extractor de ediciones de rutina de entrenamiento. El usuario quiere cambiar su plan semanal YA GUARDADO.
Responde SOLO con JSON válido, sin texto adicional, sin markdown.

Formato exacto:
{
  "ediciones": [
    {
      "dia_semana": "lunes|martes|miercoles|jueves|viernes|sabado|domingo",
      "accion": "reemplazar|agregar|eliminar|vaciar_dia",
      "ejercicio_objetivo": "nombre en minúsculas del ejercicio a cambiar/quitar, o null",
      "ejercicio_nuevo": {
        "ejercicio": "nombre en minúsculas",
        "grupo_muscular": "pecho|espalda|hombros|biceps|triceps|piernas|gluteos|core|cardio|desconocido",
        "series_objetivo": número o null,
        "reps_objetivo": "texto tipo '8-10' o número, o null",
        "notas": ""
      }
    }
  ]
}

Reglas:
- "cambia/sustituye X por Y el lunes" → accion "reemplazar", ejercicio_objetivo=X, ejercicio_nuevo=Y
- "añade/agrega/mete Z al jueves" → accion "agregar", ejercicio_objetivo=null, ejercicio_nuevo=Z
- "quita/elimina/borra X del martes" → accion "eliminar", ejercicio_objetivo=X, ejercicio_nuevo=null (ejercicio_nuevo siempre null aquí)
- "vacía/borra todo el miércoles" → accion "vaciar_dia", ejercicio_objetivo=null, ejercicio_nuevo=null
- Si el usuario no menciona series/reps/grupo muscular para el ejercicio nuevo, usa null en esos campos
- Solo incluye las ediciones que el usuario pide explícitamente, no inventes cambios adicionales
- Si menciona varios días o varios cambios, incluye una entrada por cada uno"""


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
    raise ValueError(f"No se pudo extraer JSON de: {texto[:200]}")


async def parsear_edicion_rutina(mensaje: str) -> dict | None:
    """
    Extrae ediciones estructuradas de un mensaje de edición de rutina.
    Devuelve dict con 'ediciones' (lista), o None si falla.
    """
    try:
        respuesta = await llamar_llm(
            mensajes=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": mensaje},
            ],
            modelos=MODELOS_INTENCION,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        return _extraer_json(respuesta)
    except Exception as e:
        print(f"[parsear_edicion_rutina] Error: {e}")
        return None
