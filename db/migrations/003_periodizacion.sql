-- EntrenadorIA — Fase 4: periodización / mesociclos
-- Ejecutar en Supabase SQL Editor

-- ─────────────────────────────────────────
-- TABLA MESOCICLO
-- ─────────────────────────────────────────
create table if not exists mesociclo (
    id                uuid primary key default uuid_generate_v4(),
    user_id           uuid not null,
    fase              text not null check (fase in ('hipertrofia', 'fuerza', 'deload')),
    semana_inicio     date not null,
    duracion_semanas  int not null default 4,
    objetivo_volumen  jsonb,   -- {grupo: {min_series, max_series}} para la fase
    activo            bool not null default true,
    created_at        timestamptz not null default now()
);

alter table mesociclo enable row level security;
create policy "permitir todo" on mesociclo using (true) with check (true);

create index if not exists idx_mesociclo_user_activo
    on mesociclo (user_id, activo, semana_inicio desc);
