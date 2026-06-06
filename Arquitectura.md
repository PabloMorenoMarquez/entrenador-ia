# Arquitectura Actual

## Stack

* Python
* FastAPI
* Google Sheets
* Supabase
* OpenRouter
* Render
* UptimeRobot

## Componentes principales

### API (FastAPI)

Responsable de:

* Recibir peticiones.
* Ejecutar análisis.
* Consultar RAG.
* Construir respuestas.
* Orquestar módulos.

### Motor de entrenamiento

Analiza:

* Volumen semanal.
* Fatiga.
* RIR.
* Estancamiento.
* Tendencias.
* Progresión.

Genera recomendaciones deterministas independientes del LLM.

### Memoria

Actualmente almacenada en Google Sheets.

Tablas principales:

#### Memory

Campos:

* ID
* TIPO
* CONTENIDO
* PRIORIDAD
* TAGS
* FECHA_CREACION
* ACTIVA

#### Conversaciones

Campos:

* ID_CONVERSACION
* TIMESTAMP
* ROL
* CONTENIDO

### RAG científico

Utiliza:

* Libros procesados.
* Embeddings.
* Supabase.
* Búsqueda semántica.

Actualmente devuelve contexto científico relevante para preguntas del usuario.

### LLM

Actualmente utilizado mediante OpenRouter.

Responsable de:

* Generar respuestas.
* Integrar información procedente de:

  * Memoria.
  * Motor.
  * RAG.
  * Conversación actual.