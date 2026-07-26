-- ═══════════════════════════════════════════════════════════════
-- DWH — DIMENSIONS
-- ═══════════════════════════════════════════════════════════════

-- ─── DIM_TEMPS (transversale) ───
DROP TABLE IF EXISTS dwh.dim_temps CASCADE;
CREATE TABLE dwh.dim_temps (
    id_temps        INTEGER PRIMARY KEY,      -- format YYYYMMDD
    date_complete   DATE NOT NULL UNIQUE,
    jour            INTEGER NOT NULL,
    mois            INTEGER NOT NULL,
    nom_mois        VARCHAR(20),
    trimestre       INTEGER,
    annee           INTEGER NOT NULL,
    jour_semaine    VARCHAR(20),
    est_ferie       BOOLEAN DEFAULT FALSE,
    est_weekend     BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_dim_temps_annee_mois ON dwh.dim_temps(annee, mois);
CREATE INDEX idx_dim_temps_date       ON dwh.dim_temps(date_complete);

-- ─── DIM_DP ───
DROP TABLE IF EXISTS dwh.dim_dp CASCADE;
CREATE TABLE dwh.dim_dp (
    id_dp           SERIAL PRIMARY KEY,
    code_dp         VARCHAR(20) UNIQUE NOT NULL,
    nom_dp          VARCHAR(100) NOT NULL,
    region          VARCHAR(100) DEFAULT 'Souss-Massa'
);

-- ─── DIM_CENTRE ───
DROP TABLE IF EXISTS dwh.dim_centre CASCADE;
CREATE TABLE dwh.dim_centre (
    id_centre       SERIAL PRIMARY KEY,
    code_centre     VARCHAR(50) UNIQUE NOT NULL,
    nom_centre      VARCHAR(200) NOT NULL,
    type_centre     VARCHAR(50),
    code_dp         VARCHAR(20),
    nom_dp          VARCHAR(100)
);

-- ─── DIM_TYPE_INDICATEUR_DP ───
DROP TABLE IF EXISTS dwh.dim_type_indicateur_dp CASCADE;
CREATE TABLE dwh.dim_type_indicateur_dp (
    id_type_indicateur  SERIAL PRIMARY KEY,
    code_indicateur     VARCHAR(50) UNIQUE NOT NULL,
    libelle_indicateur  VARCHAR(200) NOT NULL,
    unite               VARCHAR(50),
    categorie           VARCHAR(100)
);

-- ─── DIM_TYPE_RECLAMATION ───
DROP TABLE IF EXISTS dwh.dim_type_reclamation CASCADE;
CREATE TABLE dwh.dim_type_reclamation (
    id_type         SERIAL PRIMARY KEY,
    code            VARCHAR(50) UNIQUE NOT NULL,
    libelle         VARCHAR(200) NOT NULL,
    categorie       VARCHAR(100)
);

COMMENT ON TABLE dwh.dim_temps IS 'Dimension temporelle transversale (partagée par tous les faits)';
COMMENT ON TABLE dwh.dim_dp IS 'Dimension Direction Provinciale';
COMMENT ON TABLE dwh.dim_centre IS 'Dimension Centres de distribution';