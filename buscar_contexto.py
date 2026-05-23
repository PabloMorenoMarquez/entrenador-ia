import os
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client

load_dotenv()

openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

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

    # Construir el contexto
    contexto = ""
    for i, doc in enumerate(resultados.data):
        contexto += f"[Fuente: {doc['metadata']['libro']}]\n"
        contexto += f"{doc['content']}\n\n"

    return contexto

# Test
if __name__ == "__main__":
    pregunta = "¿Cuántas series semanales necesito para hipertrofia?"
    contexto = buscar_contexto(pregunta)
    print(contexto)