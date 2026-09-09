-- ═══════════════════════════════════════════════════════════════
-- TABLES DE RÉFÉRENCE NORMALISÉES (app_auth & app_staging)
-- ═══════════════════════════════════════════════════════════════

-- ─── 1. Rôles (Sécurité) ───
DROP TABLE IF EXISTS app_auth.ref_role CASCADE;
CREATE TABLE app_auth.ref_role (
    id_role         SERIAL PRIMARY KEY,
    code_role       VARCHAR(50) UNIQUE NOT NULL,
    libelle_role    VARCHAR(100) NOT NULL
);

-- ─── 2. Provinces ───
DROP TABLE IF EXISTS app_staging.ref_province CASCADE;
CREATE TABLE app_staging.ref_province (
    id_province     INTEGER PRIMARY KEY,
    code_province   VARCHAR(20) UNIQUE NOT NULL,
    nom_province    VARCHAR(100) NOT NULL,
    est_siege       BOOLEAN DEFAULT FALSE,
    date_creation   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── 3. Centres ───
DROP TABLE IF EXISTS app_staging.ref_centre CASCADE;
CREATE TABLE app_staging.ref_centre (
    id_centre       INTEGER PRIMARY KEY,
    code_centre     VARCHAR(50) UNIQUE NOT NULL,
    nom_centre      VARCHAR(200) NOT NULL,
    type_centre     VARCHAR(50),
    id_province     INTEGER NOT NULL REFERENCES app_staging.ref_province(id_province),
    date_creation   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── 4. Périodes (NOUVEAU - Normalisation Temporelle) ───
DROP TABLE IF EXISTS app_staging.ref_periode CASCADE;
CREATE TABLE app_staging.ref_periode (
    id_periode      SERIAL PRIMARY KEY,
    annee           SMALLINT NOT NULL,
    mois            SMALLINT NOT NULL,
    UNIQUE(annee, mois)
);

-- ─── 5. Types d'indicateurs ───
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

-- ─── 6. Types de réclamations ───
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


-- ─── Index de performance ───
CREATE INDEX idx_ref_centre_prov ON app_staging.ref_centre(id_province);
CREATE INDEX idx_ref_periode_ym ON app_staging.ref_periode(annee, mois);