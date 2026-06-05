"""
Calcula macros objetivo diarios usando el LLM a partir del perfil del usuario.
Invocado lazy desde /api/nutricion/hoy cuando no existen macros guardados,
y desde el pipeline cuando el usuario pide recalcular por chat.
"""

import json
import re

from core.llm import llamar_llm, MODELOS_PRINCIPAL

PROMPT_MACROS = """Eres un nutricionista deportivo. Calcula los macros diarios óptimos para este usuario.

Responde SOLO con un JSON válido, sin texto adicional, sin markdown:
{
  "kcal": <número entero>,
  "proteinas_g": <número entero>,
  "carbos_g": <número entero>,
  "grasas_g": <número entero>,
  "notas": "<breve justificación en 1 oración>"
}

Reglas:
- Basa el cálculo en peso, altura, edad, sexo, objetivo y nivel de actividad.
- Si falta algún dato usa estimaciones conservadoras.
- Los macros deben cuadrar con las kcal: proteinas*4 + carbos*4 + grasas*9 ≈ kcal."""


def _extraer_json_macros(texto: str) -> dict:
    texto = texto.strip()
    for patron in [
        lambda t: json.loads(t),
        lambda t: json.loads(re.search(r'```(?:json)?\s*([\s\S]*?)```', t).group(1).strip()),
        lambda t: json.loads(re.search(r'\{[\s\S]*\}', t).group(0)),
    ]:
        try:
            return patron(texto)
        except Exception:
            pass
    raise ValueError(f"No se pudo extraer JSON de macros. Respuesta: {texto[:300]}")


async def calcular_macros_objetivo(perfil: dict) -> dict:
    """
    Llama al LLM con el perfil del usuario y devuelve macros objetivo.
    Devuelve: { kcal, proteinas_g, carbos_g, grasas_g, notas, calculado_por, fecha_calculo }
    """
    from datetime import date

    perfil_texto = "\n".join(f"{k}: {v}" for k, v in perfil.items() if v)

    respuesta = await llamar_llm(
        mensajes=[
            {"role": "system", "content": PROMPT_MACROS},
            {"role": "user", "content": f"Perfil del usuario:\n{perfil_texto}"},
        ],
        modelos=MODELOS_PRINCIPAL,
        max_tokens=300,
    )

    macros = _extraer_json_macros(respuesta)

    campos_requeridos = ["kcal", "proteinas_g", "carbos_g", "grasas_g"]
    for campo in campos_requeridos:
        if campo not in macros:
            raise ValueError(f"Respuesta LLM missing campo '{campo}': {respuesta[:200]}")

    macros["calculado_por"] = "llm"
    macros["fecha_calculo"] = date.today().isoformat()
    return macros
