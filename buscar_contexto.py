import os
import hashlib
import requests
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client

load_dotenv()

openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def hash_texto(texto):
    """Genera un hash único para cada texto."""
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
    # Convertir la pregunta a embedding
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=pregunta
    )
    embedding_pregunta = response.data[0].embedding

    # Buscar chunks similares en Supabase
    resultados = supabase.rpc("buscar_documentos", {
        "query_embedding": embedding_pregunta,
        "match_count": num_resultados
    }).execute()

    # Traducir cada chunk individualmente con caché
    contexto = ""
    for doc in resultados.data:
        texto_traducido = traducir_al_español(doc['content'])
        contexto += f"[Fuente: {doc['metadata']['libro']}]\n"
        contexto += f"{texto_traducido}\n\n"

    return contexto

if __name__ == "__main__":
    import time
    inicio = time.time()
    pregunta = "¿Cuántas series semanales necesito para hipertrofia?"
    contexto = buscar_contexto(pregunta)
    print(contexto)
    print(f"\nTiempo: {int((time.time() - inicio) * 1000)}ms")