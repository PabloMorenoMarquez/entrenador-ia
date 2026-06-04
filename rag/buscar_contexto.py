import os
import hashlib
import requests
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client

load_dotenv()

openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

LIBROS_POR_CATEGORIA = {
    "entrenamiento": [
        "Muscle and Strength Pyramid",
        "Periodization",
        "Bompa",
        "Helms"
    ],
    "nutricion": [
        "Sports-Nutrition",
        "Practical applications in sports nutrition",
        "Fink",
        "Ryan"
    ],
    "circadiano": [
        "Circadian",
        "Why We Sleep",
        "Eat to Beat",
        "Carnivore",
        "Light"
    ]
}

PALABRAS_CLAVE = {
    "entrenamiento": [
        "serie", "rep", "ejercicio", "entreno", "entrenamiento", "peso",
        "músculo", "fuerza", "hipertrofia", "volumen", "descanso", "RIR",
        "progresión", "fatiga", "deload", "periodización", "frecuencia"
    ],
    "nutricion": [
        "comer", "comida", "proteína", "carbohidrato", "grasa", "caloría",
        "dieta", "nutrición", "alimento", "macros", "déficit", "superávit",
        "suplemento", "creatina", "omega", "vitamina", "hidratación"
    ],
    "circadiano": [
        "sueño", "dormir", "luz", "sol", "circadiano", "melatonina",
        "cortisol", "ritmo", "mañana", "noche", "descanso", "recuperación",
        "frío", "ducha", "naturaleza", "ayuno", "horario"
    ]
}


def detectar_categoria(pregunta):
    pregunta_lower = pregunta.lower()
    puntuaciones = {}
    for categoria, palabras in PALABRAS_CLAVE.items():
        puntuaciones[categoria] = sum(1 for p in palabras if p in pregunta_lower)
    max_p = max(puntuaciones.values())
    if max_p == 0:
        return None
    return max(puntuaciones, key=puntuaciones.get)


def hash_texto(texto):
    return hashlib.md5(texto.encode()).hexdigest()


def _traducir_con_llm(texto: str) -> str:
    """Llama al LLM para traducir. Solo se ejecuta si no hay caché."""
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
    """
    Traduce una lista de docs al español usando caché en Supabase.
    Hace UN solo SELECT para todos los hashes (batch lookup).
    Solo llama al LLM para los chunks sin caché.
    Devuelve {chunk_hash: texto_traducido}.
    """
    hashes = [hash_texto(doc["content"]) for doc in docs]
    hash_a_contenido = {hash_texto(doc["content"]): doc["content"] for doc in docs}

    # Batch lookup: un solo SELECT para todos los hashes
    traducciones: dict[str, str] = {}
    try:
        resultado = (
            supabase.table("traducciones_cache")
            .select("chunk_hash,texto_traducido")
            .in_("chunk_hash", hashes)
            .execute()
        )
        for row in resultado.data:
            traducciones[row["chunk_hash"]] = row["texto_traducido"]
    except Exception as e:
        print(f"[rag] Error leyendo caché: {e}")

    # Traducir solo los que faltan
    pendientes = [h for h in hashes if h not in traducciones]
    for h in pendientes:
        texto_original = hash_a_contenido[h]
        try:
            traducido = _traducir_con_llm(texto_original)
            traducciones[h] = traducido
            # Guardar en caché
            supabase.table("traducciones_cache").insert({
                "chunk_hash": h,
                "texto_original": texto_original,
                "texto_traducido": traducido,
            }).execute()
        except Exception as e:
            print(f"[rag] Error traduciendo chunk: {e}")
            traducciones[h] = texto_original  # fallback: texto original

    return traducciones


def buscar_contexto(pregunta, num_resultados=5):
    categoria = detectar_categoria(pregunta)

    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=pregunta,
    )
    embedding_pregunta = response.data[0].embedding

    resultados = supabase.rpc("buscar_documentos", {
        "query_embedding": embedding_pregunta,
        "match_count": 20,
    }).execute()

    docs_filtrados = resultados.data
    if categoria and categoria in LIBROS_POR_CATEGORIA:
        libros_categoria = LIBROS_POR_CATEGORIA[categoria]
        filtrados = [
            doc for doc in resultados.data
            if any(libro.lower() in doc["metadata"]["libro"].lower() for libro in libros_categoria)
        ]
        if len(filtrados) >= 3:
            docs_filtrados = filtrados

    docs_filtrados = docs_filtrados[:num_resultados]

    # Un solo batch lookup + traducir solo los faltantes
    traducciones = traducir_chunks(docs_filtrados)

    contexto = ""
    if categoria:
        contexto += f"[Categoría detectada: {categoria}]\n\n"

    for doc in docs_filtrados:
        h = hash_texto(doc["content"])
        texto = traducciones.get(h, doc["content"])
        contexto += f"[Fuente: {doc['metadata']['libro']}]\n{texto}\n\n"

    return contexto


if __name__ == "__main__":
    import time
    preguntas_test = [
        "¿Cuántas series necesito para hipertrofia?",
        "¿Cuánta proteína debo comer al día?",
        "¿Cómo afecta la luz solar al sueño?"
    ]
    for pregunta in preguntas_test:
        print(f"\nPregunta: {pregunta}")
        inicio = time.time()
        contexto = buscar_contexto(pregunta)
        tiempo = int((time.time() - inicio) * 1000)
        print(contexto[:300])
        print(f"Tiempo: {tiempo}ms")
        print("---")
