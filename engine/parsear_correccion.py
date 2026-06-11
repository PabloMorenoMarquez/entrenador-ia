"""
Parsea mensajes de corrección sobre una comida ya registrada hoy.
Identifica qué alimento del registro de hoy se corrige y qué cambia (cantidad,
nombre del alimento o tipo de comida).
"""

import json
import re
from core.llm import llamar_llm, MODELOS_INTENCION

PROMPT_SISTEMA = """Eres un extractor de correcciones de registros nutricionales. El usuario quiere
corregir un dato de una comida que registró hoy (cantidad, alimento o tipo de comida).
Responde SOLO con JSON válido, sin texto adicional, sin markdown.

Formato exacto:
{
  "alimento_objetivo": "nombre del alimento ya registrado que se corrige, en minúsculas, o null si no se identifica",
  "alimento_nuevo": "nuevo nombre del alimento, o null si no cambia",
  "cantidad_g_ml_nueva": número entero o null si no cambia,
  "tipo_comida_nueva": "desayuno|almuerzo|merienda|cena|snack|otro" o null si no cambia
}

Reglas:
- alimento_objetivo: identifica a qué alimento ya registrado se refiere el usuario
  (ej. "el pollo", "la pasta de antes", "el solomillo"). Usa el nombre del alimento,
  no la frase completa del usuario.
- Si el usuario da una cantidad nueva en gramos/ml o por unidades contables, calcula
  el total y ponlo en cantidad_g_ml_nueva.
- Si no puedes identificar alimento_objetivo con razonable seguridad, responde
  alimento_objetivo: null — NO inventes un alimento."""


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


async def parsear_correccion(mensaje: str) -> dict | None:
    """
    Extrae datos de corrección de un mensaje. Devuelve dict con
    'alimento_objetivo', 'alimento_nuevo', 'cantidad_g_ml_nueva', 'tipo_comida_nueva',
    o None si falla.
    """
    try:
        respuesta = await llamar_llm(
            mensajes=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": mensaje},
            ],
            modelos=MODELOS_INTENCION,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        return _extraer_json(respuesta)
    except Exception as e:
        print(f"[parsear_correccion] Error: {e}")
        return None
