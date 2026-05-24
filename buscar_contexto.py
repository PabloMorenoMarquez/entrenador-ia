import os
import hashlib
import requests
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client

load_dotenv()

openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Categorías de libros
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
    """
    Detecta la categoría de la pregunta contando
    palabras clave de cada categoría.
    """
    pregunta_lower = pregunta.lower()
    puntuaciones = {}

    for categoria, palabras in PALABRAS_CLAVE.items():
        puntuaciones[categoria] = sum(
            1 for palabra in palabras if palabra in pregunta_lower
        )

    # Si hay empate o ninguna categoría clara, devolver None (buscar en todo)
    max_puntuacion = max(puntuaciones.values())
    if max_puntuacion == 0:
        return None

    return max(puntuaciones, key=puntuaciones.get)

def hash_texto(texto):
    return hashlib.md5(texto.encode()).hexdigest()

def traducir_al_español(texto):
    """Traduce usando OpenRouter con caché en Supabase."""
    hash_key = hash_texto(texto)

    # Buscar en caché primero
    try:
        resultado = supabase.table("traducciones_cache").select("texto_traducido").eq("chunk_hash", hash_key).execute()
        if resultado.data:
            return resultado.data[0]["texto_traducido"]
    except Exception as e:
        print(f"Error buscando en caché: {e}")

    # Si no está en caché, traducir
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json"
        },
        json={
            "model": "nvidia/nemotron-3-nano-30b-a3b:free",
            "max_tokens": 2000,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": "Eres un traductor especializado en nutrición deportiva y entrenamiento. Traduce el texto al español manteniendo términos técnicos correctos. Devuelve solo la traducción, sin explicaciones ni texto adicional."
                },
                {
                    "role": "user",
                    "content": texto
                }
            ]
        }
    )
    data = response.json()
    if "choices" not in data:
        return texto
    texto_traducido = data["choices"][0]["message"]["content"]

    # Guardar en caché
    try:
        supabase.table("traducciones_cache").insert({
            "chunk_hash": hash_key,
            "texto_original": texto,
            "texto_traducido": texto_traducido
        }).execute()
    except Exception as e:
        print(f"Error guardando en caché: {e}")

    return texto_traducido

def buscar_contexto(pregunta, num_resultados=5):
    # Detectar categoría
    categoria = detectar_categoria(pregunta)

    # Convertir la pregunta a embedding
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=pregunta
    )
    embedding_pregunta = response.data[0].embedding

    # Buscar chunks similares en Supabase
    resultados = supabase.rpc("buscar_documentos", {
        "query_embedding": embedding_pregunta,
        "match_count": 20  # Traemos más para filtrar después
    }).execute()

    # Filtrar por categoría si se detectó una
    docs_filtrados = resultados.data
    if categoria and categoria in LIBROS_POR_CATEGORIA:
        libros_categoria = LIBROS_POR_CATEGORIA[categoria]
        docs_filtrados = [
            doc for doc in resultados.data
            if any(libro.lower() in doc['metadata']['libro'].lower()
                   for libro in libros_categoria)
        ]
        # Si el filtro deja muy pocos resultados, usar todos
        if len(docs_filtrados) < 3:
            docs_filtrados = resultados.data

    # Coger los mejores num_resultados
    docs_filtrados = docs_filtrados[:num_resultados]

    # Traducir cada chunk con caché
    contexto = ""
    if categoria:
        contexto += f"[Categoría detectada: {categoria}]\n\n"

    for doc in docs_filtrados:
        texto_traducido = traducir_al_español(doc['content'])
        contexto += f"[Fuente: {doc['metadata']['libro']}]\n"
        contexto += f"{texto_traducido}\n\n"

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