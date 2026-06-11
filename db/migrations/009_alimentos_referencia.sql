-- Migración: tabla canónica de macros por 100g + columnas de origen en registro_comidas
-- Ejecutar en Supabase SQL Editor

create table if not exists alimentos_referencia (
    id            uuid primary key default uuid_generate_v4(),
    nombre        text not null,
    nombre_norm   text not null,
    aliases       text[] not null default '{}',
    kcal_100      numeric not null,
    proteinas_100 numeric not null,
    carbos_100    numeric not null,
    grasas_100    numeric not null,
    fibra_100     numeric,
    fuente        text not null default 'curado' check (fuente in ('curado', 'bedca', 'usda', 'off')),
    off_barcode   text,
    verificado    bool not null default true,
    created_at    timestamptz not null default now()
);
alter table alimentos_referencia enable row level security;
create policy "permitir todo" on alimentos_referencia using (true) with check (true);
create unique index if not exists idx_alimentos_ref_norm on alimentos_referencia (nombre_norm);
create index if not exists idx_alimentos_ref_aliases on alimentos_referencia using gin (aliases);

-- Origen del dato de cada fila registrada
alter table registro_comidas
    add column if not exists fuente_datos    text not null default 'estimado' check (fuente_datos in ('verificado', 'estimado', 'usuario')),
    add column if not exists alimento_ref_id uuid references alimentos_referencia(id),
    add column if not exists estimado        bool not null default true;

-- Seed mínimo: alimentos críticos / frecuentes con macros verificados (BEDCA/USDA)
insert into alimentos_referencia
    (nombre, nombre_norm, aliases, kcal_100, proteinas_100, carbos_100, grasas_100, fibra_100, fuente, verificado)
values
    ('solomillo de cerdo', 'solomillo de cerdo', '{"lomo de cerdo magro","solomillo de cerdo magro","filete de cerdo"}', 120, 22, 0, 3.5, 0, 'bedca', true),
    ('lomo de cerdo', 'lomo de cerdo', '{"filete de lomo de cerdo"}', 139, 21.5, 0, 5.4, 0, 'bedca', true),
    ('pechuga de pollo', 'pechuga de pollo', '{"filete de pollo","pollo a la plancha"}', 165, 31, 0, 3.6, 0, 'bedca', true),
    ('muslo de pollo', 'muslo de pollo', '{"contramuslo de pollo"}', 209, 18, 0, 15, 0, 'bedca', true),
    ('pavo pechuga', 'pavo pechuga', '{"pechuga de pavo","filete de pavo"}', 135, 29, 0, 1, 0, 'bedca', true),
    ('ternera magra', 'ternera magra', '{"filete de ternera"}', 158, 21.6, 0, 7.7, 0, 'bedca', true),
    ('salmón', 'salmon', '{}', 208, 20, 0, 13, 0, 'bedca', true),
    ('atún al natural', 'atun al natural', '{"atun en lata al natural"}', 116, 26, 0, 1, 0, 'bedca', true),
    ('merluza', 'merluza', '{}', 86, 17.8, 0, 1.3, 0, 'bedca', true),
    ('gambas', 'gambas', '{"langostinos","camarones"}', 99, 24, 0.2, 0.3, 0, 'bedca', true),
    ('huevo', 'huevo', '{"huevo entero"}', 155, 13, 1.1, 11, 0, 'bedca', true),
    ('clara de huevo', 'clara de huevo', '{}', 52, 11, 0.7, 0.2, 0, 'bedca', true),
    ('leche entera', 'leche entera', '{}', 61, 3.2, 4.8, 3.3, 0, 'bedca', true),
    ('yogur natural', 'yogur natural', '{}', 61, 3.5, 4.7, 3.3, 0, 'bedca', true),
    ('queso fresco', 'queso fresco', '{}', 98, 11, 3.4, 4.3, 0, 'bedca', true),
    ('jamón serrano', 'jamon serrano', '{}', 241, 31, 0, 13, 0, 'bedca', true),
    ('jamón cocido', 'jamon cocido', '{"fiambre de jamon"}', 110, 18, 1, 3.8, 0, 'bedca', true),
    ('chorizo', 'chorizo', '{}', 455, 24, 1.6, 38, 0, 'bedca', true),
    ('tofu', 'tofu', '{}', 76, 8, 1.9, 4.8, 0.3, 'usda', true),
    ('arroz blanco cocido', 'arroz blanco cocido', '{"arroz cocido"}', 130, 2.7, 28, 0.3, 0.4, 'bedca', true),
    ('arroz integral cocido', 'arroz integral cocido', '{}', 123, 2.6, 25.8, 1, 1.6, 'bedca', true),
    ('pasta cocida', 'pasta cocida', '{"macarrones cocidos","espaguetis cocidos"}', 131, 5, 25, 1.1, 1.8, 'bedca', true),
    ('quinoa cocida', 'quinoa cocida', '{}', 120, 4.4, 21.3, 1.9, 2.8, 'usda', true),
    ('avena', 'avena', '{"copos de avena"}', 389, 16.9, 66, 6.9, 10.6, 'bedca', true),
    ('pan blanco', 'pan blanco', '{}', 265, 9, 49, 3.2, 2.7, 'bedca', true),
    ('pan integral', 'pan integral', '{}', 247, 13, 41, 3.4, 7, 'bedca', true),
    ('patata cocida', 'patata cocida', '{"papa cocida"}', 87, 1.9, 20, 0.1, 1.8, 'bedca', true),
    ('lentejas cocidas', 'lentejas cocidas', '{}', 116, 9, 20, 0.4, 7.9, 'bedca', true),
    ('garbanzos cocidos', 'garbanzos cocidos', '{}', 164, 8.9, 27, 2.6, 7.6, 'bedca', true),
    ('judías blancas cocidas', 'judias blancas cocidas', '{"alubias blancas cocidas"}', 127, 8.7, 23, 0.5, 6.3, 'bedca', true),
    ('plátano', 'platano', '{"banana"}', 89, 1.1, 23, 0.3, 2.6, 'bedca', true),
    ('manzana', 'manzana', '{}', 52, 0.3, 14, 0.2, 2.4, 'bedca', true),
    ('naranja', 'naranja', '{}', 47, 0.9, 12, 0.1, 2.4, 'bedca', true),
    ('tomate', 'tomate', '{}', 18, 0.9, 3.9, 0.2, 1.2, 'bedca', true),
    ('lechuga', 'lechuga', '{}', 15, 1.4, 2.9, 0.2, 1.3, 'bedca', true),
    ('brócoli', 'brocoli', '{}', 34, 2.8, 7, 0.4, 2.6, 'bedca', true),
    ('zanahoria', 'zanahoria', '{}', 41, 0.9, 10, 0.2, 2.8, 'bedca', true),
    ('aguacate', 'aguacate', '{}', 160, 2, 8.5, 14.7, 6.7, 'bedca', true),
    ('aceite de oliva', 'aceite de oliva', '{}', 884, 0, 0, 100, 0, 'bedca', true),
    ('almendras', 'almendras', '{}', 579, 21, 22, 50, 12.5, 'bedca', true)
on conflict (nombre_norm) do nothing;
