-- ============================================================
-- Fichier : 01_staging_tables.sql
-- Projet  : SRM Souss-Massa DWH
-- Date    : Juillet 2026
-- ============================================================

-- TODO: Ajouter les instructions SQL ici
-- ============================================================
-- Fichier : 01_staging_tables.sql
-- Objectif: 6 tables staging alimentees par Streamlit
-- ============================================================

SET search_path TO staging;

-- ────────────────────────────────────────────
-- 1. INDICATEURS DP
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS staging.indicateurs_dp CASCADE;

CREATE TABLE staging.indicateurs_dp (
    id_saisie           SERIAL PRIMARY KEY,
    id_province         INTEGER NOT NULL,
    id_centre           INTEGER,
    code_indicateur     VARCHAR(20) NOT NULL,
    annee               INTEGER NOT NULL CHECK (annee BETWEEN 2020 AND 2050),
    mois                INTEGER NOT NULL CHECK (mois BETWEEN 1 AND 12),
    valeur              NUMERIC(18, 4),
    commentaire         TEXT,
    saisi_par           VARCHAR(100) NOT NULL,
    date_saisie         TIMESTAMP DEFAULT NOW(),
    modifie_par         VARCHAR(100),
    date_modification   TIMESTAMP,
    statut              VARCHAR(20) DEFAULT 'BROUILLON' 
                        CHECK (statut IN ('BROUILLON', 'VALIDE', 'TRAITE', 'REJETE')),
    est_traite          BOOLEAN DEFAULT FALSE,
    date_traitement     TIMESTAMP,
    CONSTRAINT uk_indicateurs_dp 
        UNIQUE (id_province, id_centre, code_indicateur, annee, mois)
);

COMMENT ON TABLE staging.indicateurs_dp IS 
    'Saisie des 21 indicateurs mensuels par province/centre';


-- ────────────────────────────────────────────
-- 2. RECLAMATIONS DP
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS staging.reclamations_dp CASCADE;

CREATE TABLE staging.reclamations_dp (
    id_saisie           SERIAL PRIMARY KEY,
    id_province         INTEGER NOT NULL,
    id_centre           INTEGER,
    code_type_reclam    VARCHAR(20) NOT NULL,
    annee               INTEGER NOT NULL CHECK (annee BETWEEN 2020 AND 2050),
    mois                INTEGER NOT NULL CHECK (mois BETWEEN 1 AND 12),
    nombre              INTEGER,
    temps_coupure_h     NUMERIC(10, 2),
    delai_traitement_j  NUMERIC(10, 2),
    commentaire         TEXT,
    saisi_par           VARCHAR(100) NOT NULL,
    date_saisie         TIMESTAMP DEFAULT NOW(),
    modifie_par         VARCHAR(100),
    date_modification   TIMESTAMP,
    statut              VARCHAR(20) DEFAULT 'BROUILLON'
                        CHECK (statut IN ('BROUILLON', 'VALIDE', 'TRAITE', 'REJETE')),
    est_traite          BOOLEAN DEFAULT FALSE,
    date_traitement     TIMESTAMP,
    CONSTRAINT uk_reclamations_dp 
        UNIQUE (id_province, id_centre, code_type_reclam, annee, mois)
);

COMMENT ON TABLE staging.reclamations_dp IS 
    'Saisie des 10 types de reclamations mensuelles';


-- ────────────────────────────────────────────
-- 3. RENDEMENTS ETAGE
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS staging.rendements_etage CASCADE;

CREATE TABLE staging.rendements_etage (
    id_saisie           SERIAL PRIMARY KEY,
    id_etage            INTEGER NOT NULL,
    annee               INTEGER NOT NULL CHECK (annee BETWEEN 2020 AND 2050),
    mois                INTEGER NOT NULL CHECK (mois BETWEEN 1 AND 12),
    nombre_clients      INTEGER,
    volume_facture_m3   NUMERIC(18, 2),
    volume_amene_m3     NUMERIC(18, 2),
    rendement           NUMERIC(6, 4),
    commentaire         TEXT,
    saisi_par           VARCHAR(100) NOT NULL,
    date_saisie         TIMESTAMP DEFAULT NOW(),
    modifie_par         VARCHAR(100),
    date_modification   TIMESTAMP,
    statut              VARCHAR(20) DEFAULT 'BROUILLON'
                        CHECK (statut IN ('BROUILLON', 'VALIDE', 'TRAITE', 'REJETE')),
    est_traite          BOOLEAN DEFAULT FALSE,
    date_traitement     TIMESTAMP,
    CONSTRAINT uk_rendements_etage 
        UNIQUE (id_etage, annee, mois)
);

COMMENT ON TABLE staging.rendements_etage IS 
    'Rendements mensuels par etage de pression';


-- ────────────────────────────────────────────
-- 4. VOLUMES AMENES
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS staging.volumes_amenes CASCADE;

CREATE TABLE staging.volumes_amenes (
    id_saisie           SERIAL PRIMARY KEY,
    id_etage            INTEGER NOT NULL,
    annee               INTEGER NOT NULL CHECK (annee BETWEEN 2020 AND 2050),
    mois                INTEGER NOT NULL CHECK (mois BETWEEN 1 AND 12),
    volume_m3           NUMERIC(18, 2),
    commentaire         TEXT,
    saisi_par           VARCHAR(100) NOT NULL,
    date_saisie         TIMESTAMP DEFAULT NOW(),
    modifie_par         VARCHAR(100),
    date_modification   TIMESTAMP,
    statut              VARCHAR(20) DEFAULT 'BROUILLON'
                        CHECK (statut IN ('BROUILLON', 'VALIDE', 'TRAITE', 'REJETE')),
    est_traite          BOOLEAN DEFAULT FALSE,
    date_traitement     TIMESTAMP,
    CONSTRAINT uk_volumes_amenes 
        UNIQUE (id_etage, annee, mois)
);

COMMENT ON TABLE staging.volumes_amenes IS 
    'Volumes d''eau amenes par etage et par mois';


-- ────────────────────────────────────────────
-- 5. LINEAIRES (etage/secteur)
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS staging.lineaires CASCADE;

CREATE TABLE staging.lineaires (
    id_saisie           SERIAL PRIMARY KEY,
    type_element        VARCHAR(20) NOT NULL 
                        CHECK (type_element IN ('ETAGE', 'SECTEUR')),
    id_element          INTEGER NOT NULL,
    nom_element         VARCHAR(100),
    lineaire_km         NUMERIC(12, 3),
    lineaire_m          NUMERIC(15, 2),
    annee_reference     INTEGER NOT NULL,
    commentaire         TEXT,
    saisi_par           VARCHAR(100) NOT NULL,
    date_saisie         TIMESTAMP DEFAULT NOW(),
    modifie_par         VARCHAR(100),
    date_modification   TIMESTAMP,
    statut              VARCHAR(20) DEFAULT 'BROUILLON'
                        CHECK (statut IN ('BROUILLON', 'VALIDE', 'TRAITE', 'REJETE')),
    est_traite          BOOLEAN DEFAULT FALSE,
    date_traitement     TIMESTAMP,
    CONSTRAINT uk_lineaires 
        UNIQUE (type_element, id_element, annee_reference)
);

COMMENT ON TABLE staging.lineaires IS 
    'Lineaires de reseau par etage ou secteur';


-- ────────────────────────────────────────────
-- 6. MATRICE AFFECTATION Loc_Sec_Etage
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS staging.matrice_affectation CASCADE;

CREATE TABLE staging.matrice_affectation (
    id_saisie           SERIAL PRIMARY KEY,
    num_loc             INTEGER NOT NULL,
    num_sec             INTEGER NOT NULL,
    code_etage_num      INTEGER NOT NULL,
    code_loc_sec        VARCHAR(20),
    nom_etage           VARCHAR(100),
    commentaire         TEXT,
    saisi_par           VARCHAR(100) NOT NULL,
    date_saisie         TIMESTAMP DEFAULT NOW(),
    modifie_par         VARCHAR(100),
    date_modification   TIMESTAMP,
    statut              VARCHAR(20) DEFAULT 'BROUILLON'
                        CHECK (statut IN ('BROUILLON', 'VALIDE', 'TRAITE', 'REJETE')),
    est_traite          BOOLEAN DEFAULT FALSE,
    date_traitement     TIMESTAMP,
    CONSTRAINT uk_matrice_affectation 
        UNIQUE (num_loc, num_sec, code_etage_num)
);

COMMENT ON TABLE staging.matrice_affectation IS 
    'Matrice de correspondance Localite/Secteur/Etage';


-- ────────────────────────────────────────────
-- Verification
-- ────────────────────────────────────────────
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_schema = 'staging' AND table_name = t.table_name) AS nb_colonnes
FROM information_schema.tables t
WHERE table_schema = 'staging'
ORDER BY table_name;