-- Agrupa la tabla "conversaciones" (hasta ahora un único log continuo) en
-- conversaciones independientes (sesiones de chat), para poder mostrarlas
-- como una lista navegable en vez de un hilo único sin fin.

alter table conversaciones add column if not exists chat_id uuid;

-- Backfill: todo el historial existente pasa a formar UNA conversación "legacy"
-- (no se pierde nada; simplemente queda agrupado como un único chat antiguo).
update conversaciones set chat_id = '00000000-0000-0000-0000-000000000001'
    where chat_id is null;

alter table conversaciones alter column chat_id set not null;
alter table conversaciones alter column chat_id set default uuid_generate_v4();

create index if not exists idx_conversaciones_user_chat
    on conversaciones (user_id, chat_id, timestamp);
