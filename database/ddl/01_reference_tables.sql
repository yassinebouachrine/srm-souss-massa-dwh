-- ═══════════════════════════════════════════════════════════════
-- TABLES DE RÉFÉRENCE — Provinces, Centres, Types
-- Utilisées par l'application Streamlit
-- ═══════════════════════════════════════════════════════════════

-- ─── Table des provinces ───
DROP TABLE IF EXISTS app_staging.ref_province CASCADE;
CREATE TABLE app_staging.ref_province (
    id_province         INTEGER PRIMARY KEY,
    code_province       VARCHAR(20) UNIQUE NOT NULL,
    nom_province        VARCHAR(100) NOT NULL,
    est_siege           BOOLEAN DEFAULT FALSE,
    date_creation       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── Table des centres ───
DROP TABLE IF EXISTS app_staging.ref_centre CASCADE;
CREATE TABLE app_staging.ref_centre (
    id_centre           INTEGER PRIMARY KEY,
    code_centre         VARCHAR(50) UNIQUE NOT NULL,
    nom_centre          VARCHAR(200) NOT NULL,
    type_centre         VARCHAR(50),
    id_province         INTEGER REFERENCES app_staging.ref_province(id_province),
    date_creation       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── Table des types d'indicateurs ───
DROP TABLE IF EXISTS app_staging.ref_type_indicateur CASCADE;
CREATE TABLE app_staging.ref_type_indicateur (
    id_type_indicateur  SERIAL PRIMARY KEY,
    code_indicateur     VARCHAR(50) UNIQUE NOT NULL,
    libelle_indicateur  VARCHAR(200) NOT NULL,
    unite               VARCHAR(50),
    categorie           VARCHAR(100),
    ordre_affichage     INTEGER DEFAULT 0,
    est_actif           BOOLEAN DEFAULT TRUE,
    date_creation       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── Table des types de réclamations ───
DROP TABLE IF EXISTS app_staging.ref_type_reclamation CASCADE;
CREATE TABLE app_staging.ref_type_reclamation (
    id_type_reclamation SERIAL PRIMARY KEY,
    code_type           VARCHAR(50) UNIQUE NOT NULL,
    libelle_reclamation VARCHAR(200) NOT NULL,
    categorie_reclamation VARCHAR(100),
    est_comptage        BOOLEAN DEFAULT TRUE,
    est_duree           BOOLEAN DEFAULT FALSE,
    ordre_affichage     INTEGER DEFAULT 0,
    est_actif           BOOLEAN DEFAULT TRUE,
    date_creation       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── Index ───
CREATE INDEX IF NOT EXISTS idx_ref_centre_province ON app_staging.ref_centre(id_province);
CREATE INDEX IF NOT EXISTS idx_ref_indic_categorie ON app_staging.ref_type_indicateur(categorie);
CREATE INDEX IF NOT EXISTS idx_ref_reclam_categorie ON app_staging.ref_type_reclamation(categorie_reclamation);

COMMENT ON TABLE app_staging.ref_province IS 'Référentiel des 6 provinces de Souss-Massa';
COMMENT ON TABLE app_staging.ref_centre IS 'Référentiel des centres de distribution';
COMMENT ON TABLE app_staging.ref_type_indicateur IS 'Référentiel des indicateurs de performance DP';
COMMENT ON TABLE app_staging.ref_type_reclamation IS 'Référentiel des types de réclamations';