-- Renombra claves para nombre único en el sistema:
--   ipc_desagregados.id          -> id_ipc  (PK del rubro)
--   ipc_desagregados_valores.id_ipc_desagregado -> id_ipc  (FK -> ipc_desagregados.id_ipc)
-- La PK de cada fila en ipc_desagregados_valores sigue siendo "id" (surrogate de observación).
--
-- Ejecutar en Azure/psql ANTES de recrear vistas. Luego: python _create_views.py

DROP VIEW IF EXISTS v_ipc_contribucion CASCADE;
DROP VIEW IF EXISTS v_ipc_inflacion CASCADE;

ALTER TABLE ipc_desagregados RENAME COLUMN id TO id_ipc;

ALTER TABLE ipc_desagregados_valores
    RENAME COLUMN id_ipc_desagregado TO id_ipc;

-- Secuencia del SERIAL del maestro (nombre estándar PostgreSQL)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'S' AND c.relname = 'ipc_desagregados_id_seq'
    ) THEN
        ALTER SEQUENCE ipc_desagregados_id_seq RENAME TO ipc_desagregados_id_ipc_seq;
    END IF;
END $$;
