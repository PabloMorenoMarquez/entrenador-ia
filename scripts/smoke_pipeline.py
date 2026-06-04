"""
Smoke test del pipeline e2e contra Sheets/Supabase reales.
Ejecutar desde la raíz del proyecto:
    python scripts/smoke_pipeline.py

Requiere .env configurado con todas las claves.
"""

import asyncio
import sys
import os
import time

# Force UTF-8 on Windows console — LLM responses contain non-ASCII chars
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Añadir raíz al path para que los imports del proyecto funcionen
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from pipeline import procesar_mensaje

CASOS = [
    {
        "nombre": "saludo_general",
        "mensaje": "Hola, soy Pablo",
        "descripcion": "Saludo simple — debe activar solo perfil+memory, sin motor ni RAG",
    },
    {
        "nombre": "pregunta_entreno",
        "mensaje": "¿Cuántas series debería hacer para ganar masa muscular?",
        "descripcion": "Pregunta entrenamiento — debe activar motor + RAG",
    },
    {
        "nombre": "pregunta_nutricion",
        "mensaje": "¿Cuánta proteína necesito comer al día para ganar músculo?",
        "descripcion": "Pregunta nutrición — debe activar RAG",
    },
    {
        "nombre": "registro_entreno",
        "mensaje": "Acabo de terminar el entreno: press de banca 4 series de 8 reps a 70kg, me sobraron 2",
        "descripcion": "Registro de entreno — debe detectar tipo registro_entreno",
    },
]


async def ejecutar_caso(caso: dict) -> dict:
    nombre = caso["nombre"]
    print(f"\n{'='*60}")
    print(f"CASO: {nombre}")
    print(f"Mensaje: {caso['mensaje']}")
    print(f"Objetivo: {caso['descripcion']}")
    print("-" * 60)

    inicio = time.time()
    error = None
    respuesta = None

    try:
        respuesta = await procesar_mensaje(caso["mensaje"])
        latencia_ms = int((time.time() - inicio) * 1000)
        print(f"[OK] {latencia_ms}ms")
        print(f"Respuesta ({len(respuesta)} chars): {respuesta[:200]}{'...' if len(respuesta) > 200 else ''}")
    except Exception as e:
        latencia_ms = int((time.time() - inicio) * 1000)
        error = str(e)
        print(f"[ERROR] {latencia_ms}ms")
        print(f"Excepcion: {error}")

    return {
        "nombre": nombre,
        "ok": error is None,
        "latencia_ms": latencia_ms,
        "error": error,
        "chars_respuesta": len(respuesta) if respuesta else 0,
    }


async def main():
    print("=" * 60)
    print("SMOKE TEST — Pipeline e2e Entrenador IA")
    print("=" * 60)

    resultados = []
    for caso in CASOS:
        resultado = await ejecutar_caso(caso)
        resultados.append(resultado)
        # Pausa entre casos — evita 429 de Sheets API (60 reads/min)
        await asyncio.sleep(15)

    # Resumen
    print(f"\n{'='*60}")
    print("RESUMEN")
    print("=" * 60)
    ok = sum(1 for r in resultados if r["ok"])
    total = len(resultados)
    print(f"Pasados: {ok}/{total}")

    for r in resultados:
        icono = "[OK]" if r["ok"] else "[ERROR]"
        latencia = f"{r['latencia_ms']}ms"
        chars = f"{r['chars_respuesta']}c"
        error = f" -- {r['error'][:60]}" if r["error"] else ""
        print(f"  {icono} {r['nombre']:<25} {latencia:>8}  {chars:>6}{error}")

    lentos = [r for r in resultados if r["latencia_ms"] > 8000 and r["ok"]]
    if lentos:
        print(f"\n[AVISO] Casos lentos (>8s): {', '.join(r['nombre'] for r in lentos)}")

    if ok < total:
        print("\n[FALLO] Smoke test FALLIDO -- corrige los errores antes de desplegar.")
        sys.exit(1)
    else:
        print("\n[PASADO] Smoke test OK -- pipeline funciona e2e.")


if __name__ == "__main__":
    asyncio.run(main())
