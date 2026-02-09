-- Schema PostgreSQL para series_tiempo
-- Migrado desde SQLite

-- Eliminar tablas existentes (orden: dependientes primero)
DROP TABLE IF EXISTS maestro_precios CASCADE;
DROP TABLE IF EXISTS maestro CASCADE;
DROP TABLE IF EXISTS filtros_graph_pais CASCADE;
DROP TABLE IF EXISTS graph CASCADE;
DROP TABLE IF EXISTS variables CASCADE;
DROP TABLE IF EXISTS sub_familia CASCADE;
DROP TABLE IF EXISTS familia CASCADE;
DROP TABLE IF EXISTS tipo_serie CASCADE;
DROP TABLE IF EXISTS pais_grupo CASCADE;

-- Tablas de referencia (orden por dependencias)
CREATE TABLE IF NOT EXISTS pais_grupo (
    id_pais INTEGER PRIMARY KEY,
    nombre_pais_grupo VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS familia (
    id_familia INTEGER PRIMARY KEY,
    nombre_familia VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS tipo_serie (
    id_tipo_serie INTEGER PRIMARY KEY,
    nombre_tipo_serie VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS sub_familia (
    id_sub_familia INTEGER PRIMARY KEY,
    nombre_sub_familia VARCHAR(255) NOT NULL UNIQUE,
    id_familia INTEGER,
    FOREIGN KEY (id_familia) REFERENCES familia(id_familia)
);

CREATE TABLE IF NOT EXISTS variables (
    id_variable INTEGER PRIMARY KEY,
    id_nombre_variable VARCHAR(255) NOT NULL,
    id_sub_familia INTEGER,
    nominal_o_real CHAR(1),
    moneda VARCHAR(10),
    id_tipo_serie INTEGER,
    FOREIGN KEY (id_sub_familia) REFERENCES sub_familia(id_sub_familia)
);

CREATE TABLE IF NOT EXISTS graph (
    id_graph INTEGER PRIMARY KEY,
    nombre_graph VARCHAR(255) NOT NULL,
    selector VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS filtros_graph_pais (
    id_graph INTEGER,
    id_pais INTEGER,
    PRIMARY KEY (id_graph, id_pais),
    FOREIGN KEY (id_graph) REFERENCES graph(id_graph),
    FOREIGN KEY (id_pais) REFERENCES pais_grupo(id_pais)
);

-- Tabla maestro (id puede ser INTEGER si se migra con valores explícitos)
CREATE TABLE IF NOT EXISTS maestro (
    id INTEGER PRIMARY KEY,
    nombre TEXT,
    tipo TEXT,
    fuente TEXT,
    periodicidad TEXT,
    unidad TEXT,
    categoria TEXT,
    activo INTEGER,
    moneda TEXT,
    nominal_real TEXT,
    link TEXT,
    mercado TEXT,
    es_cotizacion INTEGER,
    pais VARCHAR(100),
    id_variable INTEGER,
    id_pais INTEGER,
    script_update TEXT,
    FOREIGN KEY (id_variable) REFERENCES variables(id_variable),
    FOREIGN KEY (id_pais) REFERENCES pais_grupo(id_pais)
);

-- Tabla principal de precios
CREATE TABLE IF NOT EXISTS maestro_precios (
    id SERIAL PRIMARY KEY,
    id_variable INTEGER NOT NULL,
    id_pais INTEGER NOT NULL,
    fecha DATE NOT NULL,
    valor NUMERIC(18, 6) NOT NULL,
    FOREIGN KEY (id_variable) REFERENCES variables(id_variable),
    FOREIGN KEY (id_pais) REFERENCES pais_grupo(id_pais)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_variables_id_sub_familia ON variables(id_sub_familia);
CREATE INDEX IF NOT EXISTS idx_sub_familia_id_familia ON sub_familia(id_familia);
CREATE INDEX IF NOT EXISTS idx_filtros_graph_pais_id_graph ON filtros_graph_pais(id_graph);
CREATE INDEX IF NOT EXISTS idx_filtros_graph_pais_id_pais ON filtros_graph_pais(id_pais);
CREATE INDEX IF NOT EXISTS idx_maestro_precios_id_variable ON maestro_precios(id_variable);
CREATE INDEX IF NOT EXISTS idx_maestro_precios_id_pais ON maestro_precios(id_pais);
CREATE INDEX IF NOT EXISTS idx_maestro_precios_fecha ON maestro_precios(fecha);
CREATE INDEX IF NOT EXISTS idx_maestro_precios_variable_pais_fecha ON maestro_precios(id_variable, id_pais, fecha);
