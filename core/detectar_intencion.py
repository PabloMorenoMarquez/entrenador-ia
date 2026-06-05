"""
Detecta la intención del mensaje del usuario.
Decide qué sheets leer, si activar el motor y si consultar el RAG.
Usa un modelo pequeño y rápido — la tarea es solo clasificar.
"""

import json
import re
from core.llm import llamar_llm, MODELOS_INTENCION

# Todas las sheets disponibles para que el modelo pueda elegir
SHEETS_DISPONIBLES = [
    "perfil_usuario",
    "dias_tipicos",
    "plan_semanal",
    "objetivos",
    "alimentos_disponibles",
    "memory",
]

PROMPT_SISTEMA = """Clasifica el mensaje del usuario y responde SOLO con un JSON válido, sin texto adicional, sin markdown.

Formato exacto:
{
  "tipo": "entrenamiento|nutricion|registro_entreno|registro_comida|recalcular_macros|general",
  "sheets_necesarias": ["array con nombres de sheets"],
  "necesita_motor": true o false,
  "necesita_rag": true o false
}

Sheets disponibles: perfil_usuario, dias_tipicos, plan_semanal, objetivos, alimentos_disponibles, memory

Reglas de clasificación:
- entrenamiento: preguntas sobre ejercicios, progresión, fatiga, plan, series, repeticiones → motor: true, rag: true, sheets: [perfil_usuario, plan_semanal, dias_tipicos, objetivos, memory]
- nutricion: preguntas sobre comida, macros, calorías, dieta, suplementos → motor: false, rag: true, sheets: [perfil_usuario, objetivos, alimentos_disponibles, memory]
- registro_entreno: el usuario registra lo que ha entrenado → motor: true, rag: false, sheets: [perfil_usuario, plan_semanal, memory]
- registro_comida: el usuario registra lo que ha comido → motor: false, rag: false, sheets: [perfil_usuario, objetivos, alimentos_disponibles]
- recalcular_macros: el usuario pide recalcular sus macros objetivo, ajustar calorías, cambiar objetivos nutricionales → motor: false, rag: false, sheets: [perfil_usuario, objetivos, memory]
- general: saludos, preguntas generales, conversación → motor: false, rag: false, sheets: [perfil_usuario, memory]

Incluye siempre perfil_usuario y memory en sheets_necesarias."""


def _extraer_json(texto: str) -> dict:
    """
    Extrae y parsea JSON de la respuesta del LLM de forma robusta.
    Maneja: JSON puro, code fences, texto alrededor, comillas simples.
    """
    texto = texto.strip()

    # 1. Parseo directo
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass

    # 2. Extraer de code fences ```json ... ``` o ``` ... ```
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', texto)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # 3. Buscar el primer bloque { ... } en el texto
    match = re.search(r'\{[\s\S]*?\}', texto)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # 4. Buscar el bloque más grande { ... } (para JSONs con arrays)
    match = re.search(r'\{[\s\S]*\}', texto)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # 5. Último recurso: comillas simples → dobles (modelos que devuelven Python dicts)
    try:
        return json.loads(texto.replace("'", '"'))
    except json.JSONDecodeError:
        pass

    # Log para depuración
    print(f"[detectar_intencion] No se pudo parsear JSON. Respuesta raw: {texto[:300]}")
    raise ValueError(f"No se pudo extraer JSON válido de la respuesta del modelo.")


# Fallback cuando la detección falla — no rompe el pipeline
INTENCION_FALLBACK = {
    "tipo": "general",
    "sheets_necesarias": ["perfil_usuario", "objetivos", "memory"],
    "necesita_motor": False,
    "necesita_rag": False,
}


async def detectar_intencion(mensaje: str) -> dict:
    """
    Clasifica el mensaje y devuelve un dict con:
    - tipo: categoría del mensaje
    - sheets_necesarias: qué sheets leer
    - necesita_motor: si activar el motor de entrenamiento
    - necesita_rag: si consultar el RAG científico
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

        contenido_limpio = _extraer_json(respuesta)

        intencion = contenido_limpio

        # Validar que las sheets solicitadas existan
        intencion["sheets_necesarias"] = [
            s for s in intencion.get("sheets_necesarias", [])
            if s in SHEETS_DISPONIBLES
        ]

        # Asegurar que siempre hay sheets mínimas
        for sheet_minima in ["perfil_usuario", "objetivos", "memory"]:
            if sheet_minima not in intencion["sheets_necesarias"]:
                intencion["sheets_necesarias"].append(sheet_minima)

        return intencion

    except Exception as e:
        print(f"[detectar_intencion] Error: {e}. Usando fallback.")
        return INTENCION_FALLBACK