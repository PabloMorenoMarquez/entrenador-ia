import os
import time
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
from supabase import create_client

load_dotenv()

openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100
)

def generar_embeddings_lote(textos):
    """Genera embeddings de varios chunks a la vez en una sola llamada API"""
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=textos
    )
    return [item.embedding for item in response.data]

def procesar_pdf(ruta_pdf):
    nombre_libro = os.path.basename(ruta_pdf)
    print(f"\nProcesando: {nombre_libro}")

    loader = PyPDFLoader(ruta_pdf)
    paginas = loader.load()
    print(f"  → {len(paginas)} páginas cargadas")

    chunks = splitter.split_documents(paginas)
    print(f"  → {len(chunks)} chunks generados")

    # Procesar en lotes de 50 chunks
    LOTE = 50
    total = len(chunks)

    for i in range(0, total, LOTE):
        lote = chunks[i:i+LOTE]
        textos = [c.page_content for c in lote]

        # Generar todos los embeddings del lote en una sola llamada
        embeddings = generar_embeddings_lote(textos)

        # Preparar filas para insertar en Supabase
        filas = [
            {
                "content": lote[j].page_content,
                "metadata": {
                    "libro": nombre_libro,
                    "pagina": lote[j].metadata.get("page", 0)
                },
                "embedding": embeddings[j]
            }
            for j in range(len(lote))
        ]

        # Insertar lote completo de golpe
        supabase.table("documents").insert(filas).execute()

        print(f"  → {min(i+LOTE, total)}/{total} chunks guardados")

        # Pausa pequeña para no saturar la API
        time.sleep(0.5)

    print(f"  ✓ {nombre_libro} completado")

carpeta = "libros"
for archivo in os.listdir(carpeta):
    if archivo.endswith(".pdf"):
        procesar_pdf(os.path.join(carpeta, archivo))

print("\n✓ Todos los libros procesados")