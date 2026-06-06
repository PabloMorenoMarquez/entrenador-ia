-- EntrenadorIA — Fase 5: plan nutricional con timing
-- Ejecutar en Supabase SQL Editor

create table if not exists plan_nutricional (
    id              uuid primary key default uuid_generate_v4(),
    user_id         uuid not null,
    fecha           date not null,
    hora_entreno    time,
    tomas           jsonb not null default '[]',
    notas           text,
    generado_por    text default 'llm',
    created_at      timestamptz not null default now(),
    unique(user_id, fecha)
);

alter table plan_nutricional enable row level security;
create policy "permitir todo" on plan_nutricional using (true) with check (true);

create index if not exists idx_plan_nutricional_user_fecha
    on plan_nutricional (user_id, fecha desc);
