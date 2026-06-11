"""
Cliente OpenFoodFacts: lookup de macros/100g para alimentos envasados/de marca.
Best-effort, síncrono con timeout corto — si falla, el caller cae a estimación LLM.
"""

import requests

OFF_URL = "https://world.openfoodfacts.org/cgi/search.pl"
TIMEOUT = 1.5
HEADERS = {"User-Agent": "EntrenadorIA/1.0 (entrenador-ia@example.com)"}


def buscar_off(nombre: str) -> dict | None:
    """
    Busca `nombre` en OpenFoodFacts. Devuelve dict con macros/100g + metadata
    lista para cachear en alimentos_referencia, o None si no hay match útil
    o la API no responde a tiempo.
    """
    try:
        resp = requests.get(
            OFF_URL,
            params={
                "search_terms": nombre,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page_size": 5,
                "fields": "product_name,code,nutriments",
            },
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        productos = resp.json().get("products") or []
    except Exception as e:
        print(f"[off_client] Error consultando OpenFoodFacts: {e}")
        return None

    for producto in productos:
        nutrientes = producto.get("nutriments") or {}
        kcal = nutrientes.get("energy-kcal_100g")
        proteinas = nutrientes.get("proteins_100g")
        carbos = nutrientes.get("carbohydrates_100g")
        grasas = nutrientes.get("fat_100g")
        if kcal is None or proteinas is None or carbos is None or grasas is None:
            continue
        return {
            "nombre": producto.get("product_name") or nombre,
            "kcal_100": kcal,
            "proteinas_100": proteinas,
            "carbos_100": carbos,
            "grasas_100": grasas,
            "fibra_100": nutrientes.get("fiber_100g"),
            "off_barcode": producto.get("code"),
        }
    return None
