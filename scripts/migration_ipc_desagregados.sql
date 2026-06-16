-- Migración aditiva: IPC Uruguay desagregado (no ejecuta DROP de otras tablas).
-- Requiere que exista pais_grupo.id_pais = 858 si se usan las FKs con datos.

CREATE TABLE IF NOT EXISTS ipc_desagregados (
    id SERIAL PRIMARY KEY,
    id_pais INTEGER NOT NULL DEFAULT 858 REFERENCES pais_grupo(id_pais),
    division VARCHAR(32),
    grupo VARCHAR(32),
    clase VARCHAR(32),
    subclase VARCHAR(32),
    producto VARCHAR(64),
    descripcion TEXT,
    etiqueta VARCHAR(96),
    ponderacion NUMERIC(18, 8),
    nivel VARCHAR(16) NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_ipc_desagregados_natural
    ON ipc_desagregados (
        id_pais,
        COALESCE(division, ''),
        COALESCE(grupo, ''),
        COALESCE(clase, ''),
        COALESCE(subclase, ''),
        COALESCE(producto, '')
    );

CREATE INDEX IF NOT EXISTS idx_ipc_desagregados_id_pais ON ipc_desagregados(id_pais);
CREATE INDEX IF NOT EXISTS idx_ipc_desagregados_pais_nivel ON ipc_desagregados (id_pais, nivel);

CREATE TABLE IF NOT EXISTS ipc_desagregados_valores (
    id SERIAL PRIMARY KEY,
    id_ipc_desagregado INTEGER NOT NULL REFERENCES ipc_desagregados(id) ON DELETE CASCADE,
    id_pais INTEGER NOT NULL DEFAULT 858 REFERENCES pais_grupo(id_pais),
    fecha DATE NOT NULL,
    valor NUMERIC(18, 6) NOT NULL,
    UNIQUE (id_ipc_desagregado, fecha)
);

CREATE INDEX IF NOT EXISTS idx_ipc_desag_valores_rubro_fecha
    ON ipc_desagregados_valores(id_ipc_desagregado, fecha);
CREATE INDEX IF NOT EXISTS idx_ipc_desag_valores_pais_fecha
    ON ipc_desagregados_valores(id_pais, fecha);
