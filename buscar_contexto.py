import os
import requests
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client

load_dotenv()

openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def traducir_al_español(texto):
    """Traduce usando OpenRouter con modelo gratuito."""
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
    return data["choices"][0]["message"]["content"]

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

    # Construir el contexto traducido
    contexto = ""
    for doc in resultados.data:
        texto_traducido = traducir_al_español(doc['content'])
        contexto += f"[Fuente: {doc['metadata']['libro']}]\n"
        contexto += f"{texto_traducido}\n\n"

    return contexto

if __name__ == "__main__":
    pregunta = "¿Cuántas series semanales necesito para hipertrofia?"
    contexto = buscar_contexto(pregunta)
    print(contexto)