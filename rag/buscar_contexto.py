import os
import hashlib
import requests
from dotenv import load_dotenv
from openai import OpenAI
from db.supabase_client import get_client

load_dotenv()

openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _sb():
    return get_client()


# Categorías como metadato de boost (ya no son un gate duro)
LIBROS_POR_CATEGORIA = {
    "entrenamiento": [
        "Muscle and Strength Pyramid", "Periodization", "Bompa", "Helms",
    ],
    "nutricion": [
        "Sports-Nutrition", "Practical applications in sports nutrition", "Fink", "Ryan",
    ],
    "circadiano": [
        "Circadian", "Why We Sleep", "Eat to Beat", "Carnivore", "Light",
    ],
}

# Keywords por categoría (para boost suave, no para filtrar)
_KEYWORDS_CATEGORIA = {
    "entrenamiento": [
        "serie", "rep", "ejercicio", "entreno", "entrenamiento", "peso", "músculo",
        "fuerza", "hipertrofia", "volumen", "descanso", "rir", "progresión", "fatiga",
        "deload", "periodización", "frecuencia", "mesociclo", "macrociclo", "microciclo",
        "rm", "1rm", "squat", "sentadilla", "press", "dominadas", "remo",
    ],
    "nutricion": [
        "comer", "comida", "proteína", "carbohidrato", "grasa", "caloría", "dieta",
        "nutrición", "alimento", "macros", "déficit", "superávit", "suplemento",
        "creatina", "omega", "vitamina", "hidratación", "leucina", "aminoácido",
        "mps", "síntesis proteica", "timing", "pre-entreno", "post-entreno",
    ],
    "circadiano": [
        "sueño", "dormir", "luz", "sol", "circadiano", "melatonina", "cortisol",
        "ritmo", "mañana", "noche", "recuperación", "frío", "horario", "cronotipo",
        "hrv", "descanso", "rem", "sueño profundo",
    ],
}

# Términos técnicos que incrementan complejidad percibida
_TERMINOS_TECNICOS = {
    "mesociclo", "macrociclo", "microciclo", "periodización", "deload",
    "hipertrofia", "rm", "1rm", "rir", "mps", "leucina", "creatina",
    "hrv", "vo2", "cortisol", "melatonina", "circadiano", "cronotipo",
    "superávit", "déficit", "aminoácido", "glucógeno",
}


def _detectar_categoria_boost(pregunta: str) -> str | None:
    """Detecta categoría dominante para boost suave (no filtra). Retorna None si empate."""
    lower = pregunta.lower()
    puntuaciones = {
        cat: sum(1 for kw in kws if kw in lower)
        for cat, kws in _KEYWORDS_CATEGORIA.items()
    }
    max_p = max(puntuaciones.values())
    if max_p == 0:
        return None
    # Solo retorna categoría si tiene ventaja clara (≥2 puntos sobre el segundo)
    ordenado = sorted(puntuaciones.values(), reverse=True)
    if len(ordenado) >= 2 and ordenado[0] - ordenado[1] < 2:
        return None  # demasiado ambiguo para filtrar
    return max(puntuaciones, key=puntuaciones.get)


def _calcular_num_chunks(pregunta: str) -> int:
    """
    Chunks adaptativos según complejidad de la pregunta.
    Simple: 4 | Medio: 7 | Complejo: 10
    """
    lower = pregunta.lower()
    palabras = lower.split()
    n_palabras = len(palabras)
    n_tecnicos = sum(1 for t in _TERMINOS_TECNICOS if t in lower)

    # Señales de pregunta compleja
    es_planificacion = any(kw in lower for kw in [
        "planific", "programa", "mesociclo", "periodiz", "bloque", "fase",
        "semana", "meses", "cómo organiz", "estructura",
    ])
    es_comparativa = any(kw in lower for kw in [
        "diferencia", "mejor", "peor", "vs", "comparar", "cuál es mejor",
        "pros y contras", "ventajas",
    ])
    es_causal = any(kw in lower for kw in ["por qué", "porqué", "razón", "causa", "mecanismo"])

    puntos = 0
    if n_palabras > 15:
        puntos += 1
    if n_tecnicos >= 2:
        puntos += 1
    if es_planificacion:
        puntos += 2
    if es_comparativa:
        puntos += 1
    if es_causal:
        puntos += 1

    if puntos >= 3:
        return 10
    if puntos >= 1:
        return 7
    return 4


def hash_texto(texto):
    return hashlib.md5(texto.encode()).hexdigest()


def _traducir_con_llm(texto: str) -> str:
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json",
        },
        json={
            "model": "openai/gpt-4o-mini",
            "max_tokens": 2000,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Eres un traductor especializado en nutrición deportiva y entrenamiento. "
                        "Traduce el texto al español manteniendo términos técnicos correctos. "
                        "Devuelve solo la traducción, sin explicaciones ni texto adicional."
                    ),
                },
                {"role": "user", "content": texto},
            ],
        },
        timeout=30,
    )
    data = response.json()
    if "choices" not in data:
        return texto
    return data["choices"][0]["message"]["content"]


def traducir_chunks(docs: list[dict]) -> dict[str, str]:
    """Traduce docs al español con caché Supabase. Batch lookup de hashes."""
    hashes = [hash_texto(doc["content"]) for doc in docs]
    hash_a_contenido = {hash_texto(doc["content"]): doc["content"] for doc in docs}

    traducciones: dict[str, str] = {}
    try:
        resultado = (
            _sb().table("traducciones_cache")
            .select("chunk_hash,texto_traducido")
            .in_("chunk_hash", hashes)
            .execute()
        )
        for row in resultado.data:
            traducciones[row["chunk_hash"]] = row["texto_traducido"]
    except Exception as e:
        print(f"[rag] Error leyendo caché: {e}")

    pendientes = [h for h in hashes if h not in traducciones]
    for h in pendientes:
        texto_original = hash_a_contenido[h]
        try:
            traducido = _traducir_con_llm(texto_original)
            traducciones[h] = traducido
            _sb().table("traducciones_cache").insert({
                "chunk_hash": h,
                "texto_original": texto_original,
                "texto_traducido": traducido,
            }).execute()
        except Exception as e:
            print(f"[rag] Error traduciendo chunk: {e}")
            traducciones[h] = texto_original

    return traducciones


def buscar_contexto(pregunta: str, num_resultados: int | None = None) -> str:
    """
    Búsqueda RAG profesional:
    - Recupera 40 chunks por similaridad pura (sin gate de categoría)
    - Boost suave +0.05 a chunks de la categoría dominante detectada
    - Chunks adaptativos: 4 simple / 7 medio / 10 complejo
    - Traducción con caché (sin re-traducir)
    """
    categoria = _detectar_categoria_boost(pregunta)
    n_chunks = num_resultados if num_resultados is not None else _calcular_num_chunks(pregunta)

    # Embed query
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=pregunta,
    )
    embedding_pregunta = response.data[0].embedding

    # Recuperar pool amplio (40) para que el boost de categoría tenga efecto
    resultados = _sb().rpc("buscar_documentos", {
        "query_embedding": embedding_pregunta,
        "match_count": 40,
    }).execute()

    docs = resultados.data or []

    # Boost suave: categoría detectada → +0.05 en score de similaridad
    if categoria and categoria in LIBROS_POR_CATEGORIA:
        libros_cat = LIBROS_POR_CATEGORIA[categoria]
        def _score(doc):
            libro = (doc.get("metadata") or {}).get("libro", "")
            bonus = 0.05 if any(lib.lower() in libro.lower() for lib in libros_cat) else 0
            return doc.get("similarity", 0) + bonus
        docs = sorted(docs, key=_score, reverse=True)

    docs = docs[:n_chunks]

    if not docs:
        return ""

    traducciones = traducir_chunks(docs)

    partes = []
    if categoria:
        partes.append(f"[Área: {categoria} | {n_chunks} fragmentos]\n")

    for doc in docs:
        h = hash_texto(doc["content"])
        texto = traducciones.get(h, doc["content"])
        libro = (doc.get("metadata") or {}).get("libro", "Fuente desconocida")
        partes.append(f"[Fuente: {libro}]\n{texto}")

    return "\n\n".join(partes)


if __name__ == "__main__":
    import time
    preguntas_test = [
        "¿Cuántas series necesito para hipertrofia?",
        "¿Cómo planifico un mesociclo de fuerza de 6 semanas?",
        "¿Cuánta proteína debo comer al día?",
        "¿Cómo afecta la luz solar al sueño y al rendimiento deportivo?",
        "¿Qué suplementos tienen evidencia científica sólida?",
    ]
    for pregunta in preguntas_test:
        n = _calcular_num_chunks(pregunta)
        cat = _detectar_categoria_boost(pregunta)
        print(f"\nPregunta: {pregunta}")
        print(f"  → chunks: {n}, categoría: {cat}")
        inicio = time.time()
        ctx = buscar_contexto(pregunta)
        tiempo = int((time.time() - inicio) * 1000)
        print(ctx[:400])
        print(f"  Tiempo: {tiempo}ms")
        print("---")
