-- Nivel jerárquico explícito en el maestro IPC (opción A).
-- Ejecutar una vez en bases que ya tienen ipc_desagregados.

ALTER TABLE ipc_desagregados ADD COLUMN IF NOT EXISTS nivel VARCHAR(16);

-- Regla: la fila más detallada es la que tiene el último código no nulo.
UPDATE ipc_desagregados SET nivel = CASE
    WHEN BTRIM(division::text) = '99'
         AND (grupo IS NULL OR BTRIM(grupo::text) = '')
         AND (clase IS NULL OR BTRIM(clase::text) = '')
         AND (subclase IS NULL OR BTRIM(subclase::text) = '')
         AND (producto IS NULL OR BTRIM(producto::text) = '') THEN 'general'
    WHEN producto IS NOT NULL AND BTRIM(producto::text) <> '' THEN 'producto'
    WHEN subclase IS NOT NULL AND BTRIM(subclase::text) <> '' THEN 'subclase'
    WHEN clase IS NOT NULL AND BTRIM(clase::text) <> '' THEN 'clase'
    WHEN grupo IS NOT NULL AND BTRIM(grupo::text) <> '' THEN 'grupo'
    WHEN division IS NOT NULL AND BTRIM(division::text) <> '' THEN 'division'
    ELSE 'division'
END
WHERE nivel IS NULL;

UPDATE ipc_desagregados SET nivel = 'general'
WHERE BTRIM(division::text) = '99'
  AND (grupo IS NULL OR BTRIM(grupo::text) = '')
  AND (clase IS NULL OR BTRIM(clase::text) = '')
  AND (subclase IS NULL OR BTRIM(subclase::text) = '')
  AND (producto IS NULL OR BTRIM(producto::text) = '')
  AND nivel <> 'general';

ALTER TABLE ipc_desagregados ALTER COLUMN nivel SET NOT NULL;

ALTER TABLE ipc_desagregados DROP CONSTRAINT IF EXISTS chk_ipc_desagregados_nivel;
ALTER TABLE ipc_desagregados ADD CONSTRAINT chk_ipc_desagregados_nivel
    CHECK (nivel IN ('general', 'division', 'grupo', 'clase', 'subclase', 'producto'));

CREATE INDEX IF NOT EXISTS idx_ipc_desagregados_pais_nivel
    ON ipc_desagregados (id_pais, nivel);
