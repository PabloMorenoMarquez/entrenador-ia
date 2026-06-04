"""
Parsea mensajes de registro de comida en datos estructurados.
LLM extrae alimentos, cantidades y macros estimados de texto libre.
"""

import json
import re
from core.llm import llamar_llm, MODELOS_INTENCION

PROMPT_SISTEMA = """Eres un extractor de datos nutricionales. El usuario ha registrado lo que ha comido.
Responde SOLO con JSON válido, sin texto adicional, sin markdown.

Formato exacto:
{
  "alimentos": [
    {
      "alimento": "nombre en minúsculas",
      "cantidad_g_ml": número entero o null,
      "calorias": número entero estimado o null,
      "proteinas_g": número decimal o null,
      "carbos_g": número decimal o null,
      "grasas_g": número decimal o null,
      "fibra_g": número decimal o null,
      "notas": ""
    }
  ],
  "comida": {
    "tipo_comida": "desayuno|almuerzo|merienda|cena|snack|otro",
    "notas": ""
  }
}

Reglas:
- Estima macros con conocimiento nutricional estándar (por 100g si no se especifica cantidad)
- Si no se menciona cantidad usa porción típica en gramos
- tipo_comida: infiere por contexto o hora mencionada
- Cada alimento separado en el array
- Si no puedes estimar algo usa null
- Redondea calorías y macros a 1 decimal máximo"""


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


async def parsear_comida(mensaje: str) -> dict | None:
    """
    Extrae datos estructurados de un mensaje de registro de comida.
    Devuelve dict con 'alimentos' y 'comida', o None si falla.
    """
    try:
        respuesta = await llamar_llm(
            mensajes=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": mensaje},
            ],
            modelos=MODELOS_INTENCION,
            max_tokens=800,
        )
        return _extraer_json(respuesta)
    except Exception as e:
        print(f"[parsear_comida] Error: {e}")
        return None
