-- Migración F7: tablas que reemplazan Google Sheets
-- Ejecutar en Supabase SQL Editor

-- Conversaciones
create table if not exists conversaciones (
    id          uuid primary key default uuid_generate_v4(),
    user_id     uuid not null,
    timestamp   timestamptz not null default now(),
    rol         text not null check (rol in ('user', 'assistant')),
    contenido   text not null
);
alter table conversaciones enable row level security;
create policy "permitir todo" on conversaciones using (true) with check (true);
create index if not exists idx_conversaciones_user_ts
    on conversaciones (user_id, timestamp desc);

-- Macros objetivo
create table if not exists macros_objetivo (
    id              uuid primary key default uuid_generate_v4(),
    user_id         uuid not null,
    fecha_calculo   timestamptz not null default now(),
    periodo         text not null default 'dia',
    kcal            int,
    proteinas_g     int,
    carbos_g        int,
    grasas_g        int,
    notas           text,
    activa          bool not null default true
);
alter table macros_objetivo enable row level security;
create policy "permitir todo" on macros_objetivo using (true) with check (true);
create index if not exists idx_macros_objetivo_user
    on macros_objetivo (user_id, activa desc, fecha_calculo desc);

-- Registro de comidas
create table if not exists registro_comidas (
    id              uuid primary key default uuid_generate_v4(),
    user_id         uuid not null,
    fecha           date not null,
    hora            time,
    tipo_comida     text,
    alimento        text not null,
    cantidad_g_ml   numeric,
    calorias        int,
    proteinas_g     numeric,
    carbos_g        numeric,
    grasas_g        numeric,
    fibra_g         numeric,
    notas           text,
    created_at      timestamptz not null default now()
);
alter table registro_comidas enable row level security;
create policy "permitir todo" on registro_comidas using (true) with check (true);
create index if not exists idx_registro_comidas_user_fecha
    on registro_comidas (user_id, fecha desc);

-- Historial de entrenamientos
create table if not exists historial_entrenamientos (
    id                       uuid primary key default uuid_generate_v4(),
    user_id                  uuid not null,
    sesion_id                text not null,
    fecha                    date not null,
    hora_inicio              time,
    hora_fin                 time,
    duracion_min             int,
    tipo_sesion              text,
    grupo_muscular_principal text,
    nivel_energia            int,
    nivel_esfuerzo           int,
    notas_sesion             text,
    created_at               timestamptz not null default now(),
    unique(user_id, sesion_id)
);
alter table historial_entrenamientos enable row level security;
create policy "permitir todo" on historial_entrenamientos using (true) with check (true);
create index if not exists idx_hist_entreno_user_fecha
    on historial_entrenamientos (user_id, fecha desc);

-- Ejercicios detalle
create table if not exists ejercicios_detalle (
    id              uuid primary key default uuid_generate_v4(),
    user_id         uuid not null,
    sesion_id       text not null,
    fecha           date not null,
    orden           int,
    ejercicio       text not null,
    grupo_muscular  text,
    series          int,
    reps_objetivo   text,
    reps_realizadas text,
    peso_kg         numeric,
    tipo_peso       text,
    descanso_seg    int,
    rir             int,
    notas           text,
    created_at      timestamptz not null default now()
);
alter table ejercicios_detalle enable row level security;
create policy "permitir todo" on ejercicios_detalle using (true) with check (true);
create index if not exists idx_ejercicios_user_sesion
    on ejercicios_detalle (user_id, sesion_id);
create index if not exists idx_ejercicios_user_fecha
    on ejercicios_detalle (user_id, fecha desc);

-- Configuración estática (perfil_usuario, dias_tipicos, plan_semanal, objetivos, alimentos_disponibles)
-- Lazy-populated desde Sheets en el primer acceso; escrita en dual-write al editar perfil
create table if not exists configuracion (
    id              uuid primary key default uuid_generate_v4(),
    user_id         uuid not null,
    hoja            text not null,
    contenido_texto text not null default '',
    datos_json      jsonb not null default '{}',
    updated_at      timestamptz not null default now(),
    unique(user_id, hoja)
);
alter table configuracion enable row level security;
create policy "permitir todo" on configuracion using (true) with check (true);
