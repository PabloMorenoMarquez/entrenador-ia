"""
Calcula macros objetivo diarios usando el LLM a partir del perfil del usuario.
Invocado lazy desde /api/nutricion/hoy cuando no existen macros guardados,
y desde el pipeline cuando el usuario pide recalcular por chat.
"""

import json
import re
from typing import Optional

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
        response_format={"type": "json_object"},
    )

    macros = _extraer_json_macros(respuesta)

    campos_requeridos = ["kcal", "proteinas_g", "carbos_g", "grasas_g"]
    for campo in campos_requeridos:
        if campo not in macros:
            raise ValueError(f"Respuesta LLM missing campo '{campo}': {respuesta[:200]}")

    macros["calculado_por"] = "llm"
    macros["fecha_calculo"] = date.today().isoformat()
    return macros


# ─────────────────────────────────────────
# TIMING NUTRICIONAL (Fase 5)
# ─────────────────────────────────────────

PROMPT_TIMING = """Eres nutricionista deportivo de élite. Genera un plan de comidas con timing exacto para HOY.

Macros objetivo diarios: {kcal} kcal | {p}g proteína | {c}g carbos | {g}g grasa
Hora de entrenamiento: {hora_entreno}
Cronotipo: {cronotipo}

Reglas obligatorias:
- 4-5 tomas. Proteína 25-40g por toma.
- Si hay entreno:
  * Pre-entreno 1.5-2h antes: carbos 40-60g, proteína 25-30g, grasa <10g
  * Post-entreno 0-1.5h después: proteína 35-45g, carbos 40-60g, grasa <8g
- Si no hay entreno: distribución uniforme.
- La suma de kcal/macros de las tomas debe cuadrar con el objetivo diario (±5%).

Responde SOLO con JSON válido, sin texto adicional:
{{
  "tomas": [
    {{
      "nombre": "Desayuno",
      "hora": "08:00",
      "proposito": "inicio_dia",
      "kcal": 500,
      "proteinas_g": 35,
      "carbos_g": 45,
      "grasas_g": 15,
      "ejemplos": ["Avena 80g con proteína en polvo 30g", "Café solo"]
    }}
  ],
  "hora_entreno": "{hora_entreno_raw}",
  "notas": "Una frase clave sobre el timing de hoy"
}}

Valores válidos para proposito: inicio_dia | pre_entreno | post_entreno | media_manana | almuerzo | merienda | cena"""


def _extraer_hora_entreno_hoy(dias_tipicos_txt: str, plan_semanal_txt: str) -> Optional[str]:
    """Extrae hora de entreno para HOY del texto de Sheets. None si no hay entreno."""
    from datetime import date as _date

    dias_es = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    dia_hoy = dias_es[_date.today().weekday()]
    texto = f"{dias_tipicos_txt}\n{plan_semanal_txt}".lower()

    # "miércoles: 18:00" | "miércoles 18h" | "miércoles - 18:00" | "miércoles(18:00)"
    for patron in [
        rf'{dia_hoy}[\s:\-\(]+(\d{{1,2}}:\d{{2}})',
        rf'{dia_hoy}[\s:\-\(]+(\d{{1,2}})h\b',
    ]:
        m = re.search(patron, texto)
        if m:
            hora = m.group(1)
            return hora if ':' in hora else f"{hora}:00"

    # Si el día aparece pero sin hora, podría ser día de entreno sin hora especificada
    if re.search(rf'\b{dia_hoy}\b', texto):
        return "18:00"  # hora por defecto si el día está listado pero sin hora

    return None


async def calcular_timing_nutricional(
    macros_objetivo: dict,
    hora_entreno: Optional[str],
    cronotipo: Optional[str] = None,
) -> dict:
    """
    Genera plan de comidas con timing anclado a la hora de entrenamiento.
    Retorna dict con 'tomas' (lista), 'hora_entreno', 'notas'.
    """
    from datetime import date

    kcal = macros_objetivo.get("kcal", 2000)
    p = macros_objetivo.get("proteinas_g", 150)
    c = macros_objetivo.get("carbos_g", 200)
    g = macros_objetivo.get("grasas_g", 70)

    hora_texto = hora_entreno or "sin entrenamiento hoy"
    tipo_crono = cronotipo or "intermedio"

    prompt = PROMPT_TIMING.format(
        kcal=kcal, p=p, c=c, g=g,
        hora_entreno=hora_texto,
        hora_entreno_raw=hora_entreno or "",
        cronotipo=tipo_crono,
    )

    respuesta = await llamar_llm(
        mensajes=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": "Genera el plan de comidas de hoy."},
        ],
        modelos=MODELOS_PRINCIPAL,
        max_tokens=800,
        response_format={"type": "json_object"},
    )

    data = _extraer_json_macros(respuesta)
    data["fecha"] = date.today().isoformat()
    return data
