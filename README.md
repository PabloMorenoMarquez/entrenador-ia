# EntrenadorIA

> **Entrenador personal inteligente** que combina un motor determinista de análisis de entrenamiento, memoria persistente del usuario, RAG científico y un LLM para generar recomendaciones personalizadas y adaptativas.

---

## ¿Qué es esto?

EntrenadorIA **no es un chatbot**. Es un sistema inteligente que actúa como coach personal de entrenamiento y nutrición, capaz de:

- Mantener **memoria persistente** del usuario (objetivos, historial, perfil físico)
- **Analizar la progresión** real: volumen, RIR, fatiga, estancamiento, tendencias
- Consultar **conocimiento científico** mediante RAG (libros de entrenamiento y nutrición)
- Usar un **LLM** para razonar y comunicar recomendaciones de forma natural
- Seguimiento de **nutrición y biométricos**
- Funcionar como **asistente conversacional continuo**

---

## Arquitectura

```
┌─────────────────────────────────────────────────┐
│                  FastAPI (api.py)               │
│        Punto de entrada HTTP + SPA              │
└─────────┬────────────────────────────┬──────────┘
          │                            │
          ▼                            ▼
┌──────────────────┐        ┌──────────────────────┐
│  pipeline.py     │        │   Endpoints REST API  │
│  Orquestador     │        │  /api/perfil          │
│  principal       │        │  /api/rutina          │
└──────┬───────────┘        │  /api/biometricos     │
       │                    │  /api/checkin         │
       │                    │  /api/medidas         │
       │                    └──────────────────────┘
       │
       ├──────────────────────────────┐
       │                              │
       ▼                              ▼
┌─────────────┐              ┌────────────────┐
│   MEMORIA   │              │ MOTOR ANÁLISIS │
│ Google      │              │ engine/        │
│ Sheets      │              │ analizar_      │
│             │              │ entrenamiento  │
└──────┬──────┘              └───────┬────────┘
       │                             │
       │                             ▼
       │                    ┌────────────────┐
       │                    │ motor_decision │
       │                    │ Recomendaciones│
       │                    │ deterministas  │
       │                    └───────┬────────┘
       │                            │
       ▼                            ▼
┌──────────────────────────────────────────────┐
│                 CORE (LLM)                   │
│  core/construir_prompt.py                    │
│  core/detectar_intencion.py                  │
│  core/evaluar_memoria.py                     │
│  core/llm.py → OpenRouter                    │
└──────────────────────────────────────────────┘
       │
       ▼
┌─────────────────┐
│   RAG CIENTÍFICO│
│ rag/buscar_     │
│ contexto.py     │
│ Supabase        │
│ Embeddings      │
└─────────────────┘
```

---

## Stack Tecnológico

| Capa | Tecnología |
|---|---|
| **Backend / API** | Python · FastAPI · Uvicorn |
| **LLM** | OpenRouter (modelos libres + de pago) |
| **Embeddings RAG** | OpenAI Embeddings |
| **Base de conocimiento** | Supabase (pgvector) |
| **Memoria** | Google Sheets (vía Service Account) |
| **Despliegue** | Render + Procfile |
| **Keep-alive** | UptimeRobot |
| **Frontend** | SPA estática servida por FastAPI (`/static`) |

---

## Estructura del Proyecto

```
EntrenadorIA/
├── api.py                      # FastAPI: endpoints HTTP + SPA
├── pipeline.py                 # Orquestador principal del flujo
├── core/
│   ├── construir_prompt.py     # Construcción del prompt dinámico
│   ├── detectar_intencion.py   # Clasificación de intención del usuario
│   ├── evaluar_memoria.py      # Selección y priorización de memorias
│   └── llm.py                  # Cliente LLM (OpenRouter)
├── engine/
│   ├── analizar_entrenamiento.py  # Análisis: volumen, RIR, fatiga, tendencias
│   ├── motor_decision.py          # Generación de recomendaciones deterministas
│   └── tests_motor.py             # Tests del motor
├── memory/
│   └── conectar_sheets.py      # Lectura/escritura en Google Sheets
├── rag/
│   └── buscar_contexto.py      # Búsqueda semántica en Supabase
├── data/
│   └── procesar_libros.py      # Pipeline de ingestión de libros (PDF → chunks → embeddings)
├── utils/
│   └── precalentar_cache.py    # Warm-up de caché al arrancar
├── static/                     # Frontend SPA (HTML/CSS/JS)
├── libros/                     # Libros de entrenamiento y nutrición (PDFs)
├── Procfile                    # Configuración de Render
├── requirements.txt
├── env.example                 # Plantilla de variables de entorno
└── .gitignore
```

---

## Modelo de Datos (Google Sheets)

El sistema utiliza un libro de Google Sheets como base de datos ligera con las siguientes hojas:

| Hoja | Descripción |
|---|---|
| `perfil_usuario` | Datos personales, físicos, nutrición, estilo de vida |
| `memory` | Memorias persistentes del usuario (tipo, prioridad, tags) |
| `conversaciones` | Historial de conversaciones con el asistente |
| `dias_tipicos` | Días de entrenamiento habituales y horarios |
| `plan_semanal` | Plan de entrenamiento semanal |
| `objetivos` | Objetivos principales y secundarios con fechas meta |
| `registro_corporal` | Peso, % grasa, medidas corporales |
| `fotos_progreso` | URLs de fotos de progreso |
| `historial_entrenamientos` | Sesiones completas con energía, esfuerzo, duración |
| `ejercicios_detalle` | Ejercicios por sesión: series, reps, peso, RIR |
| `registro_comidas` | Alimentos consumidos con macros |
| `alimentos_disponibles` | Despensa actual del usuario |
| `notas_coach` | Notas y acciones pendientes del coach |

---

## Endpoints API

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/chat` | Mensaje al asistente → respuesta generada por el pipeline |
| `GET` | `/api/chat/historial` | Historial de mensajes |
| `GET` | `/api/chat/conversaciones` | Lista de conversaciones |
| `GET/POST` | `/api/perfil` | Perfil del usuario |
| `GET` | `/api/rutina` | Última sesión de entrenamiento |
| `GET/POST` | `/api/rutina/plan` | Plan de entrenamiento semanal |
| `POST` | `/api/biometricos` | Datos del smartwatch (FC, HRV, SpO2, pasos…) |
| `POST` | `/api/checkin` | Check-in diario (fatiga, dolor, sueño, estado mental) |
| `POST` | `/api/medidas` | Medidas corporales |
| `POST` | `/api/hidratacion` | Registro de hidratación |
| `GET` | `/health` | Health check |
| `GET/HEAD` | `/ping` | Ping (para UptimeRobot) |

---

## Cómo funciona el pipeline

```
Usuario envía mensaje
        │
        ▼
1. Detectar intención  →  ¿Es sobre entrenamiento? ¿Nutrición? ¿General?
        │
        ▼
2. Cargar contexto
   ├── Leer perfil y memoria del usuario (Sheets)
   ├── Analizar últimas sesiones (engine)
   └── Buscar contexto científico relevante (RAG → Supabase)
        │
        ▼
3. Construir prompt dinámico
   └── Integrar: perfil + memorias + análisis + RAG + historial conversación
        │
        ▼
4. LLM (OpenRouter) genera respuesta
        │
        ▼
5. Post-proceso
   ├── Extraer y guardar nuevas memorias
   └── Guardar conversación en Sheets
        │
        ▼
Respuesta al usuario
```

---

## Estado del Proyecto

| Fase | Descripción | Estado |
|---|---|---|
| **Fase 1** | Estabilización (flujo básico, gestión de tokens) | ✅ 95% |
| **Fase 2** | Memoria persistente (estructura, tipos, auto-memoria) | 🔄 80-85% |
| **Fase 3** | Motor de entrenamiento (volumen, RIR, fatiga, score) | 🔄 85-90% |
| **Fase 4** | RAG científico (embeddings, Supabase, búsqueda semántica) | 🔄 75-80% |
| **Fase 5** | Cerebro IA (pipeline completo, integración de módulos) | 🚧 50-60% |
| **Fase 6** | Entrenamiento inteligente (auto-progresión, ajustes) | 🚧 35-40% |
| **Fase 7** | Nutrición (parser, macros, adaptación) | ⏳ 10-15% |
| **Fase 8** | Insights automáticos (informes, correlaciones) | ⏳ 0-5% |
| **Fase 9** | Sistema Pro (auth, multi-usuario, dashboard) | 📋 0% |

---

## Configuración y Despliegue

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/entrenador-ia.git
cd entrenador-ia
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Copia `env.example` a `.env` y rellena los valores:

```bash
cp env.example .env
```

```env
# OpenRouter (LLM)
OPENROUTER_API_KEY=tu_clave_aqui

# Modelos (se intentan en orden si hay rate limit 429)
MODELOS_INTENCION=arcee-ai/trinity-large-thinking:free,...
MODELOS_PRINCIPAL=nvidia/nemotron-3-nano-30b-a3b:free,...
MODELOS_MEMORIA=arcee-ai/trinity-large-thinking:free,...

# Google Sheets (Service Account JSON en una línea)
GOOGLE_CREDENTIALS={...}
SHEET_ID=id_de_tu_libro

# Supabase (RAG)
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=tu_clave

# OpenAI (para embeddings RAG)
OPENAI_API_KEY=tu_clave

# Usuario
USER_ID=00000000-0000-0000-0000-000000000001
API_KEY=   # dejar vacío para desarrollo
```

### 4. Arrancar en local

```bash
uvicorn api:app --reload --port 8000
```

La API quedará disponible en `http://localhost:8000`.

### 5. Despliegue en Render

El proyecto incluye un `Procfile` listo para Render:

```
web: uvicorn api:app --host 0.0.0.0 --port $PORT
```

---

## Ingestión de Conocimiento Científico (RAG)

Para añadir nuevos libros al sistema de RAG:

1. Coloca los PDFs en la carpeta `libros/`
2. Ejecuta el pipeline de procesamiento:

```bash
python data/procesar_libros.py
```

Esto generará los chunks, calculará los embeddings con OpenAI y los almacenará en Supabase con pgvector para búsqueda semántica.

---

## Seguridad

- El endpoint `/api/biometricos` acepta una `API_KEY` opcional (cabecera `X-API-Key`) para integraciones con smartwatch o apps Android.
- Las credenciales de Google se pasan como JSON en una variable de entorno (nunca se sube el archivo `credentials.json`).
- El archivo `.env` y los tokens OAuth están en `.gitignore`.

---

## Contribuciones

Este es un proyecto personal en desarrollo activo. Si tienes ideas, sugerencias o encuentras bugs, abre un issue o un PR.

---

## Licencia

MIT — libre de usar, modificar y distribuir.
