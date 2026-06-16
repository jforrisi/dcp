-- Añade columna etiqueta si la tabla ipc_desagregados ya existía sin ella.
ALTER TABLE ipc_desagregados ADD COLUMN IF NOT EXISTS etiqueta VARCHAR(96);
