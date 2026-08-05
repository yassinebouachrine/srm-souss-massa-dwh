-- ═══════════════════════════════════════════════════════════════
-- DWH — DIM_CANAL_LABEL
-- Mapping (id_pmac + canal) → libellé métier
-- Alimenté depuis Map_CanalLabel.xlsx
-- ═══════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS dwh.dim_canal_label CASCADE;
CREATE TABLE dwh.dim_canal_label (
    id_canal_label      SERIAL PRIMARY KEY,
    key_canal           VARCHAR(50) UNIQUE NOT NULL,  -- "0416|DEBIT_02"
    id_pmac             VARCHAR(20) NOT NULL,          -- "0416"
    canal               VARCHAR(50) NOT NULL,          -- "DEBIT_02"
    canal_label         VARCHAR(200) NOT NULL,         -- "Débit Sortie 10 000"
    voie                VARCHAR(20),                   -- Extrait de canal : "DEBIT"
    channel             VARCHAR(10),                   -- Extrait de canal : "02"
    fichier_source_ref  VARCHAR(255),
    date_creation       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modification   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dim_canal_label_pmac  ON dwh.dim_canal_label(id_pmac);
CREATE INDEX idx_dim_canal_label_canal ON dwh.dim_canal_label(canal);
CREATE INDEX idx_dim_canal_label_voie  ON dwh.dim_canal_label(voie);

COMMENT ON TABLE dwh.dim_canal_label IS 
    'Libellé métier lisible pour chaque canal (KeyCanal = id_pmac|canal). Alimenté depuis Map_CanalLabel.xlsx';
COMMENT ON COLUMN dwh.dim_canal_label.key_canal IS 
    'Clé métier stable : id_pmac + "|" + canal (ex: "0416|DEBIT_02")';
COMMENT ON COLUMN dwh.dim_canal_label.canal_label IS 
    'Libellé métier lisible (ex: "Débit Sortie 10 000", "PRESSION AMONT")';