"""
Lookup determinista de macros por 100g contra la tabla alimentos_referencia.
Separa la cantidad (estimada por LLM/usuario) de los macros/100g (dato verificado).
"""

import re
import unicodedata

from db.repositorio import buscar_alimento_ref_sb, crear_alimento_ref_sb
from engine.off_client import buscar_off


def normalizar(nombre: str) -> str:
    """minúsculas, sin tildes, espacios colapsados — para matching contra nombre_norm/aliases."""
    texto = nombre.strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto)


def escalar(ref: dict, cantidad_g_ml) -> dict:
    """Escala macros_100 de la referencia a la cantidad dada (gramos/ml)."""
    factor = cantidad_g_ml / 100
    campos = (
        ("kcal_100", "calorias"),
        ("proteinas_100", "proteinas_g"),
        ("carbos_100", "carbos_g"),
        ("grasas_100", "grasas_g"),
        ("fibra_100", "fibra_g"),
    )
    return {
        destino: round(ref[origen] * factor, 1) if ref.get(origen) is not None else None
        for origen, destino in campos
    }


def resolver_alimento(nombre: str, cantidad_g_ml) -> dict:
    """
    Resuelve macros/100g en 3 niveles:
    1. alimentos_referencia local (exacto o por alias) → dato curado/auditado.
    2. OpenFoodFacts (síncrono, timeout corto) → se cachea en alimentos_referencia
       (fuente='off', verificado=false) para futuras búsquedas.
    3. Si ninguno responde, deja que el LLM aporte la estimación (fuente_datos='estimado').

    Si hay match (1 o 2) y se conoce la cantidad, calcula los macros de forma
    determinista (fuente_datos='verificado').
    """
    norm = normalizar(nombre)
    ref = buscar_alimento_ref_sb(norm)

    if not ref:
        off = buscar_off(nombre)
        if off:
            ref = crear_alimento_ref_sb({
                "nombre": off["nombre"],
                "nombre_norm": norm,
                "kcal_100": off["kcal_100"],
                "proteinas_100": off["proteinas_100"],
                "carbos_100": off["carbos_100"],
                "grasas_100": off["grasas_100"],
                "fibra_100": off.get("fibra_100"),
                "fuente": "off",
                "off_barcode": off.get("off_barcode"),
                "verificado": False,
            })

    if ref and cantidad_g_ml:
        return {
            **escalar(ref, cantidad_g_ml),
            "fuente_datos": "verificado",
            "estimado": False,
            "alimento_ref_id": ref["id"],
        }
    return {
        "fuente_datos": "estimado",
        "estimado": True,
        "alimento_ref_id": ref["id"] if ref else None,
    }
