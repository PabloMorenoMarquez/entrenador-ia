"""
Pre-calienta la caché de traducciones RAG ejecutando consultas frecuentes.
Solo traduce los chunks realmente devueltos por esas queries (tipicamente 5 por query).
MUCHO mas barato que traducir todos los chunks: ~25-50 chunks en total.

Uso:
    python scripts/precalentar_cache.py
    python scripts/precalentar_cache.py --queries "hipertrofia series" "proteina diaria"
"""

import sys
import os
import time
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

# Queries frecuentes que cubren los chunks mas accedidos
QUERIES_DEFAULT = [
    # Entrenamiento
    "¿Cuántas series necesito para hipertrofia?",
    "¿Cuánta frecuencia de entrenamiento por semana?",
    "¿Cómo progresar en fuerza?",
    "¿Qué es el RIR y cómo usarlo?",
    "¿Cómo hacer deload?",
    "volumen semanal por grupo muscular",
    "periodización del entrenamiento",
    # Nutrición
    "¿Cuánta proteína debo comer al día?",
    "¿Cuántas calorías para ganar músculo?",
    "¿Cuándo tomar creatina?",
    "carbohidratos antes del entrenamiento",
    "déficit calórico para perder grasa",
    # Circadiano / recuperación
    "¿Cómo afecta el sueño al músculo?",
    "luz solar y cortisol por la mañana",
    "recuperación entre sesiones",
]


def precalentar_por_queries(queries: list[str], delay: float = 2.0):
    # Importar aquí para que dotenv esté cargado
    from rag.buscar_contexto import buscar_contexto

    print(f"Calentando caché con {len(queries)} queries...")
    print("(Solo se traducen chunks no cacheados — los ya cacheados son gratis)\n")

    for i, query in enumerate(queries, 1):
        print(f"[{i}/{len(queries)}] {query[:60]}")
        try:
            buscar_contexto(query)
            print("  OK")
        except Exception as e:
            print(f"  Error: {e}")
        time.sleep(delay)

    print("\nPrecalentado completado.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pre-calienta caché RAG por queries frecuentes")
    parser.add_argument("--queries", nargs="*", help="Queries adicionales a calentar")
    parser.add_argument("--delay", type=float, default=2.0, help="Segundos entre queries")
    args = parser.parse_args()

    queries = QUERIES_DEFAULT[:]
    if args.queries:
        queries.extend(args.queries)

    precalentar_por_queries(queries, delay=args.delay)
