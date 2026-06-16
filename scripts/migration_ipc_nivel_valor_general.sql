-- Añade el valor 'general' al CHECK de nivel y normaliza la fila IPC general (división 99).
-- Ejecutar si ya corrías migration_ipc_desagregados_nivel.sql con el CHECK de 5 valores.

ALTER TABLE ipc_desagregados DROP CONSTRAINT IF EXISTS chk_ipc_desagregados_nivel;
ALTER TABLE ipc_desagregados ADD CONSTRAINT chk_ipc_desagregados_nivel
    CHECK (nivel IN ('general', 'division', 'grupo', 'clase', 'subclase', 'producto'));

UPDATE ipc_desagregados SET nivel = 'general'
WHERE BTRIM(division::text) = '99'
  AND (grupo IS NULL OR BTRIM(grupo::text) = '')
  AND (clase IS NULL OR BTRIM(clase::text) = '')
  AND (subclase IS NULL OR BTRIM(subclase::text) = '')
  AND (producto IS NULL OR BTRIM(producto::text) = '');
