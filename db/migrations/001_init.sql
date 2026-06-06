-- EntrenadorIA — Fase 1: tablas de recuperación y biométricos
-- Ejecutar en Supabase SQL Editor
-- Todas las tablas son multi-user-ready (user_id uuid) con RLS habilitada pero permisiva por ahora.

-- ─────────────────────────────────────────
-- EXTENSIONES (ya deben existir por el RAG)
-- ─────────────────────────────────────────
create extension if not exists "uuid-ossp";

-- ─────────────────────────────────────────
-- BIOMÉTRICOS  (Watch + manual)
-- Fuente: 'manual' o 'watch'
-- Upsert por (user_id, fecha, fuente)
-- ─────────────────────────────────────────
create table if not exists biometricos (
    id              uuid primary key default uuid_generate_v4(),
    user_id         uuid not null,
    fecha           date not null,
    fuente          text not null default 'manual',  -- 'manual' | 'watch'

    -- Sueño
    sueno_horas     numeric(4,2),
    sueno_calidad   smallint check (sueno_calidad between 1 and 5),
    hora_acostarse  time,
    hora_despertar  time,
    rem_min         integer,
    profundo_min    integer,

    -- Watch (nullable; llegan de Health Connect)
    fc_reposo       integer,
    hrv             integer,
    spo2            numeric(5,2),
    pasos           integer,
    estres          smallint check (estres between 1 and 5),
    kcal_activas    integer,

    created_at      timestamptz not null default now(),

    unique (user_id, fecha, fuente)
);

alter table biometricos enable row level security;
create policy "permitir todo" on biometricos using (true) with check (true);

create index if not exists idx_biometricos_user_fecha
    on biometricos (user_id, fecha desc);

-- ─────────────────────────────────────────
-- CHECK-IN MATUTINO  (subjetivo diario)
-- ─────────────────────────────────────────
create table if not exists checkin_matutino (
    id              uuid primary key default uuid_generate_v4(),
    user_id         uuid not null,
    fecha           date not null,

    fatiga          smallint check (fatiga between 1 and 5),
    dolor_muscular  smallint check (dolor_muscular between 1 and 5),
    calidad_sueno   smallint check (calidad_sueno between 1 and 5),
    estado_mental   smallint check (estado_mental between 1 and 5),
    notas           text,

    created_at      timestamptz not null default now(),

    unique (user_id, fecha)
);

alter table checkin_matutino enable row level security;
create policy "permitir todo" on checkin_matutino using (true) with check (true);

create index if not exists idx_checkin_user_fecha
    on checkin_matutino (user_id, fecha desc);

-- ─────────────────────────────────────────
-- MEDIDAS CORPORALES
-- ─────────────────────────────────────────
create table if not exists body_measurements (
    id              uuid primary key default uuid_generate_v4(),
    user_id         uuid not null,
    fecha           date not null,

    peso_kg         numeric(5,2),
    cintura_cm      numeric(5,1),
    pecho_cm        numeric(5,1),
    brazo_cm        numeric(5,1),
    pierna_cm       numeric(5,1),
    grasa_pct       numeric(5,2),

    created_at      timestamptz not null default now(),

    unique (user_id, fecha)
);

alter table body_measurements enable row level security;
create policy "permitir todo" on body_measurements using (true) with check (true);

create index if not exists idx_measurements_user_fecha
    on body_measurements (user_id, fecha desc);

-- ─────────────────────────────────────────
-- HIDRATACIÓN  (litros diarios)
-- ─────────────────────────────────────────
create table if not exists hidratacion (
    id              uuid primary key default uuid_generate_v4(),
    user_id         uuid not null,
    fecha           date not null,
    litros          numeric(4,2) not null,
    created_at      timestamptz not null default now(),

    unique (user_id, fecha)
);

alter table hidratacion enable row level security;
create policy "permitir todo" on hidratacion using (true) with check (true);

-- ─────────────────────────────────────────
-- DOLOR / LESIONES  (registro diario dinámico)
-- ─────────────────────────────────────────
create table if not exists dolor_lesion (
    id              uuid primary key default uuid_generate_v4(),
    user_id         uuid not null,
    fecha           date not null,
    zona            text not null,       -- p.ej. "hombro derecho"
    intensidad      smallint check (intensidad between 0 and 10),
    activo          boolean not null default true,
    notas           text,
    created_at      timestamptz not null default now()
);

alter table dolor_lesion enable row level security;
create policy "permitir todo" on dolor_lesion using (true) with check (true);

create index if not exists idx_dolor_user_activo
    on dolor_lesion (user_id, activo, fecha desc);

-- ─────────────────────────────────────────
-- CRONOTIPO  (1 fila por usuario)
-- ─────────────────────────────────────────
create table if not exists cronotipo (
    id                   uuid primary key default uuid_generate_v4(),
    user_id              uuid not null unique,
    tipo                 text check (tipo in ('matutino', 'vespertino', 'intermedio')),
    hora_luz             time,
    hora_entreno_optima  time,
    ventana_comidas      jsonb,   -- {"inicio": "07:00", "fin": "19:00"}
    created_at           timestamptz not null default now(),
    updated_at           timestamptz not null default now()
);

alter table cronotipo enable row level security;
create policy "permitir todo" on cronotipo using (true) with check (true);
