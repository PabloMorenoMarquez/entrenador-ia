-- EntrenadorIA — Fase 2: memoria semántica con pgvector
-- Ejecutar en Supabase SQL Editor DESPUÉS de 001_init.sql

-- Extensión vector (ya debe existir por el RAG)
create extension if not exists vector;

-- ─────────────────────────────────────────
-- TABLA MEMORY (reemplaza Sheet "memory")
-- ─────────────────────────────────────────
create table if not exists memory (
    id               uuid primary key default uuid_generate_v4(),
    user_id          uuid not null,
    tipo             text,            -- perfil|objetivo|limitacion|preferencia|progreso|medico
    contenido        text not null,
    prioridad        int not null default 3 check (prioridad between 1 and 5),
    tags             text[],
    embedding        vector(1536),    -- text-embedding-3-small
    activa           bool not null default true,
    fecha_creacion   timestamptz not null default now(),
    fecha_expiracion timestamptz      -- null = nunca expira (prioridad 4-5)
);

alter table memory enable row level security;
create policy "permitir todo" on memory using (true) with check (true);

-- Índice ivfflat para búsqueda ANN (cosine)
create index if not exists idx_memory_embedding
    on memory using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

create index if not exists idx_memory_user_activa
    on memory (user_id, activa, prioridad desc);

-- ─────────────────────────────────────────
-- RPC: búsqueda semántica con boost de prioridad
-- Score = 0.7 * cosine_similarity + 0.3 * (prioridad/5)
-- ─────────────────────────────────────────
create or replace function buscar_memoria(
    query_embedding  vector(1536),
    p_user_id        uuid,
    match_count      int default 8,
    min_prioridad    int default 1
)
returns table (
    id               uuid,
    tipo             text,
    contenido        text,
    prioridad        int,
    fecha_creacion   timestamptz,
    similarity       float
)
language sql stable
as $$
    select
        m.id,
        m.tipo,
        m.contenido,
        m.prioridad,
        m.fecha_creacion,
        (1 - (m.embedding <=> query_embedding)) * 0.7
            + (m.prioridad::float / 5.0) * 0.3 as similarity
    from memory m
    where
        m.user_id = p_user_id
        and m.activa = true
        and m.prioridad >= min_prioridad
        and m.embedding is not null
    order by similarity desc
    limit match_count;
$$;
