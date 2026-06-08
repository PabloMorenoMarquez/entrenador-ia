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
- CANTIDADES EN UNIDADES CONTABLES (ej. "8 filetes", "3 huevos", "2 lonchas", "5 galletas"):
  van en UNA SOLA entrada del array (mismo alimento = una entrada, NUNCA una entrada
  por pieza/unidad). cantidad_g_ml y los macros de esa entrada son el TOTAL acumulado
  = peso de UNA unidad x número de unidades. "8 filetes de solomillo" es UNA entrada
  con cantidad_g_ml = suma de los 8, no 8 entradas con el total cada una (eso duplica
  el registro x8 al guardarse).
- PESO POR UNIDAD: si el usuario describe el tamaño ("como la palma de la mano",
  "pequeño", "grande", "del tamaño de un puño", o dimensiones en cm), usa ESA
  descripción para estimar el peso unitario, no un valor genérico de receta. Indica
  el cálculo en "notas" (ej. "8 filetes pequeños ~9x4cm x ~40g = 320g total").
- tipo_comida: infiere por contexto o hora mencionada
- Cada ALIMENTO DISTINTO va en su propia entrada del array (no repitas el mismo
  alimento en varias entradas — agrega sus cantidades en una sola)
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
            response_format={"type": "json_object"},
        )
        return _extraer_json(respuesta)
    except Exception as e:
        print(f"[parsear_comida] Error: {e}")
        return None
