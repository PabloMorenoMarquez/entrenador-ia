-- Migración: ampliación del seed de alimentos_referencia (Fase 7)
-- Ejecutar en Supabase SQL Editor (después de 009_alimentos_referencia.sql)

insert into alimentos_referencia
    (nombre, nombre_norm, aliases, kcal_100, proteinas_100, carbos_100, grasas_100, fibra_100, fuente, verificado)
values
    -- Carnes
    ('pollo entero con piel', 'pollo entero con piel', '{}', 239, 18.6, 0, 17.5, 0, 'bedca', true),
    ('alitas de pollo', 'alitas de pollo', '{}', 203, 17.5, 0, 14.5, 0, 'bedca', true),
    ('carne picada de ternera 5%', 'carne picada de ternera 5%', '{"carne picada magra de ternera"}', 137, 21, 0, 5, 0, 'usda', true),
    ('carne picada de ternera 15%', 'carne picada de ternera 15%', '{"carne picada de ternera"}', 215, 19, 0, 15, 0, 'usda', true),
    ('carne picada de cerdo', 'carne picada de cerdo', '{}', 263, 16.5, 0, 21.2, 0, 'bedca', true),
    ('solomillo de ternera', 'solomillo de ternera', '{"filete de solomillo de ternera"}', 131, 21.6, 0, 5, 0, 'bedca', true),
    ('entrecot de ternera', 'entrecot de ternera', '{}', 175, 20, 0, 10, 0, 'bedca', true),
    ('costillas de cerdo', 'costillas de cerdo', '{}', 277, 16, 0, 23, 0, 'bedca', true),
    ('bacon', 'bacon', '{"panceta de cerdo","panceta"}', 541, 37, 1.4, 42, 0, 'usda', true),
    ('conejo', 'conejo', '{}', 173, 21, 0, 9, 0, 'bedca', true),
    ('cordero pierna', 'cordero pierna', '{"pierna de cordero"}', 156, 20, 0, 8, 0, 'bedca', true),
    ('hígado de pollo', 'higado de pollo', '{}', 119, 17.9, 0.7, 4.8, 0, 'bedca', true),

    -- Pescados y mariscos
    ('atún fresco', 'atun fresco', '{}', 144, 23.3, 0, 4.9, 0, 'bedca', true),
    ('bacalao', 'bacalao', '{"bacalao fresco"}', 82, 17.8, 0, 0.7, 0, 'bedca', true),
    ('dorada', 'dorada', '{}', 96, 19.8, 0, 1.7, 0, 'bedca', true),
    ('lubina', 'lubina', '{}', 97, 18.4, 0, 2.5, 0, 'bedca', true),
    ('sardinas', 'sardinas', '{}', 166, 20.6, 0, 9.6, 0, 'bedca', true),
    ('boquerones', 'boquerones', '{"anchoas frescas"}', 96, 16.8, 0, 3.4, 0, 'bedca', true),
    ('caballa', 'caballa', '{}', 205, 18.6, 0, 13.9, 0, 'bedca', true),
    ('pulpo', 'pulpo', '{}', 82, 14.9, 2.2, 1, 0, 'bedca', true),
    ('calamar', 'calamar', '{"calamares"}', 92, 15.6, 3.1, 1.4, 0, 'bedca', true),
    ('mejillones', 'mejillones', '{}', 86, 11.9, 3.4, 2.2, 0, 'bedca', true),
    ('almejas', 'almejas', '{}', 74, 12.8, 2.6, 1, 0, 'bedca', true),
    ('surimi', 'surimi', '{"palitos de mar","palitos de cangrejo"}', 95, 15, 6.7, 0.9, 0, 'usda', true),

    -- Lácteos y huevos
    ('leche desnatada', 'leche desnatada', '{}', 35, 3.4, 5, 0.1, 0, 'bedca', true),
    ('leche semidesnatada', 'leche semidesnatada', '{}', 46, 3.3, 4.8, 1.6, 0, 'bedca', true),
    ('yogur griego natural', 'yogur griego natural', '{}', 99, 9, 4, 5.5, 0, 'usda', true),
    ('yogur griego 0%', 'yogur griego 0%', '{"yogur griego desnatado"}', 57, 10, 3.9, 0.2, 0, 'usda', true),
    ('queso manchego curado', 'queso manchego curado', '{"queso curado","manchego"}', 400, 26, 0.5, 33, 0, 'bedca', true),
    ('queso de burgos', 'queso de burgos', '{}', 174, 13, 3, 12, 0, 'bedca', true),
    ('queso cottage', 'queso cottage', '{}', 98, 11, 3.4, 4.3, 0, 'usda', true),
    ('queso mozzarella', 'queso mozzarella', '{}', 280, 22, 2.2, 21, 0, 'bedca', true),
    ('requesón', 'requeson', '{}', 96, 11, 3.5, 4, 0, 'bedca', true),
    ('nata para cocinar', 'nata para cocinar', '{}', 292, 2.5, 3.5, 30, 0, 'bedca', true),
    ('mantequilla', 'mantequilla', '{}', 717, 0.9, 0.1, 81, 0, 'bedca', true),
    ('queso en lonchas', 'queso en lonchas', '{"queso para sandwich"}', 330, 18, 3, 27, 0, 'usda', true),

    -- Cereales, legumbres y harinas
    ('guisantes cocidos', 'guisantes cocidos', '{}', 81, 5.4, 14, 0.4, 5.1, 'bedca', true),
    ('habas cocidas', 'habas cocidas', '{}', 88, 7.6, 14.5, 0.7, 5.4, 'bedca', true),
    ('cuscús cocido', 'cuscus cocido', '{}', 112, 3.8, 23, 0.2, 1.4, 'usda', true),
    ('maíz dulce', 'maiz dulce', '{"maiz cocido","elote"}', 96, 3.4, 19, 1.5, 2.4, 'bedca', true),
    ('pan de molde integral', 'pan de molde integral', '{}', 224, 9, 41, 3.5, 6, 'bedca', true),
    ('tortitas de maíz', 'tortitas de maiz', '{}', 384, 8, 80, 3.5, 6, 'usda', true),
    ('tortitas de arroz', 'tortitas de arroz', '{}', 387, 8, 81, 2.8, 4.2, 'usda', true),
    ('harina de trigo', 'harina de trigo', '{}', 364, 10, 76, 1, 2.7, 'bedca', true),
    ('copos de maíz', 'copos de maiz', '{"cereales de maiz","cornflakes"}', 378, 7, 84, 0.9, 3, 'usda', true),
    ('muesli', 'muesli', '{}', 362, 9.7, 66, 6, 8, 'usda', true),

    -- Frutas
    ('pera', 'pera', '{}', 57, 0.4, 15, 0.1, 3.1, 'bedca', true),
    ('fresas', 'fresas', '{}', 32, 0.7, 7.7, 0.3, 2, 'bedca', true),
    ('uvas', 'uvas', '{}', 69, 0.7, 18, 0.2, 0.9, 'bedca', true),
    ('sandía', 'sandia', '{}', 30, 0.6, 7.6, 0.2, 0.4, 'bedca', true),
    ('melón', 'melon', '{}', 34, 0.8, 8, 0.2, 0.9, 'bedca', true),
    ('piña', 'pina', '{"pina natural"}', 50, 0.5, 13, 0.1, 1.4, 'bedca', true),
    ('kiwi', 'kiwi', '{}', 61, 1.1, 15, 0.5, 3, 'bedca', true),
    ('mango', 'mango', '{}', 60, 0.8, 15, 0.4, 1.6, 'bedca', true),
    ('arándanos', 'arandanos', '{}', 57, 0.7, 14, 0.3, 2.4, 'usda', true),
    ('ciruela', 'ciruela', '{}', 46, 0.7, 11, 0.3, 1.4, 'bedca', true),
    ('melocotón', 'melocoton', '{}', 39, 0.9, 10, 0.3, 1.5, 'bedca', true),
    ('dátiles', 'datiles', '{}', 282, 2.5, 75, 0.4, 8, 'usda', true),
    ('higos', 'higos', '{}', 74, 0.8, 19, 0.3, 2.9, 'bedca', true),
    ('pasas', 'pasas', '{"uvas pasas"}', 299, 3.1, 79, 0.5, 3.7, 'bedca', true),

    -- Verduras y hortalizas
    ('pimiento rojo', 'pimiento rojo', '{}', 31, 1, 6, 0.3, 2.1, 'bedca', true),
    ('pimiento verde', 'pimiento verde', '{}', 20, 0.9, 4.6, 0.2, 1.7, 'bedca', true),
    ('cebolla', 'cebolla', '{}', 40, 1.1, 9.3, 0.1, 1.7, 'bedca', true),
    ('pepino', 'pepino', '{}', 15, 0.7, 3.6, 0.1, 0.5, 'bedca', true),
    ('calabacín', 'calabacin', '{}', 17, 1.2, 3.1, 0.3, 1, 'bedca', true),
    ('berenjena', 'berenjena', '{}', 25, 1, 6, 0.2, 3, 'bedca', true),
    ('espinacas', 'espinacas', '{}', 23, 2.9, 3.6, 0.4, 2.2, 'bedca', true),
    ('champiñones', 'champinones', '{"champinon","setas"}', 22, 3.1, 3.3, 0.3, 1, 'bedca', true),
    ('coliflor', 'coliflor', '{}', 25, 1.9, 5, 0.3, 2, 'bedca', true),
    ('judía verde', 'judia verde', '{"judias verdes"}', 31, 1.8, 7, 0.1, 3.4, 'bedca', true),
    ('calabaza', 'calabaza', '{}', 26, 1, 6.5, 0.1, 0.5, 'bedca', true),
    ('ajo', 'ajo', '{}', 149, 6.4, 33, 0.5, 2.1, 'bedca', true),
    ('apio', 'apio', '{}', 16, 0.7, 3, 0.2, 1.6, 'bedca', true),
    ('col', 'col', '{"repollo"}', 25, 1.3, 5.8, 0.1, 2.5, 'bedca', true),

    -- Frutos secos, semillas y grasas
    ('nueces', 'nueces', '{}', 654, 15, 14, 65, 6.7, 'bedca', true),
    ('anacardos', 'anacardos', '{}', 553, 18, 30, 44, 3.3, 'bedca', true),
    ('cacahuetes', 'cacahuetes', '{"manies"}', 567, 25.8, 16, 49, 8.5, 'bedca', true),
    ('pistachos', 'pistachos', '{}', 562, 20, 28, 45, 10.6, 'bedca', true),
    ('avellanas', 'avellanas', '{}', 628, 15, 17, 61, 9.7, 'bedca', true),
    ('semillas de chía', 'semillas de chia', '{"chia"}', 486, 17, 42, 31, 34, 'usda', true),
    ('semillas de lino', 'semillas de lino', '{"linaza"}', 534, 18, 29, 42, 27, 'usda', true),
    ('crema de cacahuete', 'crema de cacahuete', '{"mantequilla de cacahuete","peanut butter"}', 588, 25, 20, 50, 6, 'usda', true),
    ('aceite de coco', 'aceite de coco', '{}', 862, 0, 0, 100, 0, 'usda', true),

    -- Proteínas y bebidas vegetales
    ('proteína de suero en polvo', 'proteina de suero en polvo', '{"whey protein","proteina whey","batido de proteinas"}', 380, 75, 8, 6, 1, 'usda', true),
    ('leche de almendras', 'leche de almendras', '{}', 24, 0.5, 3, 1.1, 0.3, 'usda', true),
    ('leche de avena', 'leche de avena', '{}', 47, 1, 6.7, 1.5, 0.8, 'usda', true),
    ('hummus', 'hummus', '{}', 166, 7.9, 14, 9.6, 6, 'usda', true),
    ('edamame', 'edamame', '{}', 122, 11, 8, 5, 5.2, 'usda', true),

    -- Salsas, condimentos y dulces
    ('mayonesa', 'mayonesa', '{}', 680, 1, 1, 75, 0, 'bedca', true),
    ('ketchup', 'ketchup', '{}', 112, 1.2, 26, 0.2, 0.4, 'usda', true),
    ('mostaza', 'mostaza', '{}', 66, 4.4, 5.3, 4, 3.3, 'usda', true),
    ('miel', 'miel', '{}', 304, 0.3, 82, 0, 0.2, 'bedca', true),
    ('mermelada', 'mermelada', '{}', 250, 0.5, 62, 0.1, 1, 'bedca', true),
    ('azúcar', 'azucar', '{"azucar blanco"}', 387, 0, 100, 0, 0, 'bedca', true),
    ('chocolate negro 70%', 'chocolate negro 70%', '{"chocolate negro"}', 598, 7.8, 46, 43, 11, 'usda', true),
    ('chocolate con leche', 'chocolate con leche', '{}', 535, 7.6, 57, 30, 3.4, 'bedca', true),
    ('cacao en polvo', 'cacao en polvo', '{"cacao puro"}', 228, 19.6, 58, 14, 33, 'usda', true),

    -- Bebidas
    ('cerveza', 'cerveza', '{}', 43, 0.5, 3.6, 0, 0, 'bedca', true),
    ('vino tinto', 'vino tinto', '{}', 85, 0.1, 2.6, 0, 0, 'bedca', true),
    ('refresco de cola', 'refresco de cola', '{"cola","coca cola"}', 42, 0, 10.6, 0, 0, 'usda', true),
    ('zumo de naranja', 'zumo de naranja', '{"jugo de naranja"}', 45, 0.7, 10.4, 0.2, 0.1, 'bedca', true),

    -- Panadería
    ('pan de pita', 'pan de pita', '{}', 275, 9, 56, 1.2, 2.2, 'usda', true),
    ('bizcocho casero', 'bizcocho casero', '{"bizcocho"}', 350, 6, 50, 14, 1, 'bedca', true),
    ('galletas maría', 'galletas maria', '{}', 430, 7, 75, 12, 2, 'bedca', true)
on conflict (nombre_norm) do nothing;
