"""
Parsea mensajes de registro de entrenamiento en datos estructurados.
LLM extrae ejercicios y metadata de sesión de texto libre.
"""

import json
import re
from core.llm import llamar_llm, MODELOS_INTENCION

PROMPT_SISTEMA = """Eres un extractor de datos de entrenamiento. El usuario ha registrado lo que ha entrenado.
Responde SOLO con JSON válido, sin texto adicional, sin markdown.

Formato exacto:
{
  "ejercicios": [
    {
      "ejercicio": "nombre en minúsculas",
      "grupo_muscular": "pecho|espalda|hombros|biceps|triceps|piernas|gluteos|core|cardio|desconocido",
      "series": número o null,
      "reps_objetivo": número o null,
      "reps_realizadas": número o null,
      "peso_kg": número decimal o null,
      "tipo_peso": "barra|mancuernas|maquina|cable|peso_corporal|otro",
      "descanso_seg": número o null,
      "rir": número o null,
      "series_detalle": [
        {"numero": 1, "reps": número o null, "peso_kg": número o null, "rir": número o null, "nota": ""}
      ] o null,
      "notas": ""
    }
  ],
  "sesion": {
    "tipo_sesion": "fuerza|hipertrofia|cardio|funcional|otro",
    "grupo_muscular_principal": "nombre o null",
    "nivel_energia": número 1-5 o null,
    "nivel_esfuerzo": número 1-10 o null,
    "duracion_min": número o null,
    "notas": ""
  }
}

Reglas:
- RIR = reps que sobraron ("me sobraron 2" = rir 2, "al fallo" = rir 0)
- tipo_peso: infiere por contexto (press banca → barra, curl con mancuernas → mancuernas)
- Si no se menciona algo, usa null
- Todos los ejercicios mencionados van en el array
- series_detalle: SOLO rellénalo si el usuario describe cada serie por separado con datos distintos
  entre ellas (ej. "primera serie 10 reps a 80, segunda 8 a 80, tercera al fallo 6 a 70" o un dropset).
  Cada entrada es una serie real reportada, en orden. Si solo da un número de series y un peso/reps
  generales para todo el ejercicio (sin diferenciar serie a serie), deja series_detalle en null —
  no inventes un desglose que el usuario no ha dado."""


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


async def parsear_entreno(mensaje: str) -> dict | None:
    """
    Extrae datos estructurados de un mensaje de registro de entrenamiento.
    Devuelve dict con 'ejercicios' y 'sesion', o None si falla.
    """
    try:
        respuesta = await llamar_llm(
            mensajes=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": mensaje},
            ],
            modelos=MODELOS_INTENCION,
            max_tokens=2500,
            response_format={"type": "json_object"},
        )
        return _extraer_json(respuesta)
    except Exception as e:
        print(f"[parsear_entreno] Error: {e}")
        return None
