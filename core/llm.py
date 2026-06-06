"""
Utilidad central para llamadas a OpenRouter.
Gestiona automáticamente el fallback entre modelos cuando hay 429.
"""

import httpx
import os
import asyncio

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Modelos configurables via .env
# Fallback automático si el primero devuelve 429
MODELOS_INTENCION: list[str] = [
    m.strip()
    for m in os.environ.get("MODELOS_INTENCION", "openai/gpt-4o-mini").split(",")
    if m.strip()
]

MODELOS_PRINCIPAL: list[str] = [
    m.strip()
    for m in os.environ.get("MODELOS_PRINCIPAL", "openai/gpt-4o-mini").split(",")
    if m.strip()
]

MODELOS_MEMORIA: list[str] = [
    m.strip()
    for m in os.environ.get("MODELOS_MEMORIA", "openai/gpt-4o-mini").split(",")
    if m.strip()
]


def _get_headers() -> dict:
    return {
        "Authorization": f"Bearer {os.environ.get('OPENROUTER_API_KEY', '')}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.environ.get("APP_URL", "https://entrenador-ia.app"),
    }


async def llamar_llm(
    mensajes: list[dict],
    modelos: list[str],
    max_tokens: int = 1000,
    pausa_entre_intentos: float = 1.0,
    response_format: dict | None = None,
) -> str:
    """
    Llama al primer modelo disponible de la lista.
    Si devuelve 429, espera un momento y prueba el siguiente.
    Lanza excepción solo si todos los modelos fallan.

    response_format: p.ej. {"type": "json_object"} para forzar JSON.
    No todos los modelos de OpenRouter lo soportan; si falla, reintenta sin él.
    """
    ultimo_error = None

    for modelo in modelos:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                body: dict = {
                    "model": modelo,
                    "max_tokens": max_tokens,
                    "messages": mensajes,
                }
                if response_format:
                    body["response_format"] = response_format
                response = await client.post(
                    OPENROUTER_URL,
                    headers=_get_headers(),
                    json=body,
                )

                if response.status_code == 429:
                    ultimo_error = f"429 en {modelo}"
                    await asyncio.sleep(pausa_entre_intentos)
                    continue

                response.raise_for_status()
                data = response.json()
                msg = data["choices"][0]["message"]
                # Thinking models return content=null and put output in reasoning
                content = msg.get("content") or msg.get("reasoning") or ""
                return content

        except httpx.HTTPStatusError as e:
            ultimo_error = str(e)
            await asyncio.sleep(pausa_entre_intentos)
            continue
        except Exception as e:
            ultimo_error = str(e)
            continue

    raise RuntimeError(f"Todos los modelos fallaron. Último error: {ultimo_error}")
