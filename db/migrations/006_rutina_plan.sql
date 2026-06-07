-- Plan de rutina semanal estructurado (objetivo por día) + comparación con lo realizado.
-- Lo realizado ya vive en ejercicios_detalle (Fase 1); esta tabla guarda solo el objetivo.

create table if not exists rutina_plan (
    id              uuid primary key default uuid_generate_v4(),
    user_id         uuid not null,
    dia_semana      text not null,   -- 'lunes' .. 'domingo'
    orden           int not null default 1,
    ejercicio       text not null,
    grupo_muscular  text,
    series_objetivo int,
    reps_objetivo   text,
    notas           text,
    updated_at      timestamptz not null default now(),
    unique (user_id, dia_semana, orden)
);
alter table rutina_plan enable row level security;
create policy "permitir todo" on rutina_plan using (true) with check (true);
create index if not exists idx_rutina_plan_user_dia
    on rutina_plan (user_id, dia_semana);
