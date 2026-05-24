import os
import time
import hashlib
import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def hash_texto(texto):
    return hashlib.md5(texto.encode()).hexdigest()

def traducir_al_español(texto):
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

def ya_traducido(hash_key):
    try:
        resultado = supabase.table("traducciones_cache").select("id").eq("chunk_hash", hash_key).execute()
        return len(resultado.data) > 0
    except:
        return False

def precalentar():
    # Obtener todos los chunks de Supabase
    print("Cargando chunks de Supabase...")
    
    # Paginar de 1000 en 1000 porque Supabase tiene límite
    todos_chunks = []
    offset = 0
    while True:
        resultado = supabase.table("documents").select("content").range(offset, offset + 999).execute()
        if not resultado.data:
            break
        todos_chunks.extend(resultado.data)
        offset += 1000
        print(f"  → {len(todos_chunks)} chunks cargados")
        if len(resultado.data) < 1000:
            break

    print(f"Total: {len(todos_chunks)} chunks")

    # Traducir los que no estén en caché
    traducidos = 0
    saltados = 0
    errores = 0

    for i, chunk in enumerate(todos_chunks):
        texto = chunk["content"]
        hash_key = hash_texto(texto)

        if ya_traducido(hash_key):
            saltados += 1
            continue

        try:
            traduccion = traducir_al_español(texto)
            supabase.table("traducciones_cache").insert({
                "chunk_hash": hash_key,
                "texto_original": texto,
                "texto_traducido": traduccion
            }).execute()
            traducidos += 1

            if traducidos % 10 == 0:
                print(f"  → {traducidos} traducidos, {saltados} ya existían, {errores} errores")

            # Pausa para no saturar OpenRouter
            time.sleep(1)

        except Exception as e:
            errores += 1
            print(f"  Error en chunk {i}: {e}")
            time.sleep(2)

    print(f"\n✓ Completado: {traducidos} traducidos, {saltados} ya existían, {errores} errores")

if __name__ == "__main__":
    precalentar()