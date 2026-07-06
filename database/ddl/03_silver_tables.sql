-- ============================================================
-- Fichier : 03_silver_tables.sql
-- Projet  : SRM Souss-Massa DWH
-- Date    : Juillet 2026
-- ============================================================

-- TODO: Ajouter les instructions SQL ici
-- ============================================================
-- Fichier : 03_silver_tables.sql
-- Objectif: 5 tables Silver (donnees nettoyees)
-- ============================================================

SET search_path TO silver;

-- ────────────────────────────────────────────
-- 1. SILVER : Indicateurs DP Nettoyes
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS silver.indicateurs_dp_clean CASCADE;

CREATE TABLE silver.indicateurs_dp_clean (
    id_silver           BIGSERIAL PRIMARY KEY,
    id_bronze_source    BIGINT,
    id_province         INTEGER NOT NULL,
    id_centre           INTEGER,
    code_indicateur     VARCHAR(20) NOT NULL,
    annee               INTEGER NOT NULL,
    mois                INTEGER NOT NULL,
    valeur              NUMERIC(18, 4),
    unite               VARCHAR(20),
    categorie           VARCHAR(50),
    commentaire         TEXT,
    saisi_par           VARCHAR(100),
    date_saisie         TIMESTAMP,
    est_valide          BOOLEAN DEFAULT TRUE,
    score_qualite       NUMERIC(3, 2),
    erreurs_validation  TEXT[],
    date_transformation TIMESTAMP DEFAULT NOW(),
    version_etl         VARCHAR(20) DEFAULT 'v1.0'
);


-- ────────────────────────────────────────────
-- 2. SILVER : Reclamations Nettoyees
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS silver.reclamations_dp_clean CASCADE;

CREATE TABLE silver.reclamations_dp_clean (
    id_silver           BIGSERIAL PRIMARY KEY,
    id_bronze_source    BIGINT,
    id_province         INTEGER NOT NULL,
    id_centre           INTEGER,
    code_type_reclam    VARCHAR(20) NOT NULL,
    annee               INTEGER NOT NULL,
    mois                INTEGER NOT NULL,
    nombre              INTEGER,
    temps_coupure_h     NUMERIC(10, 2),
    delai_traitement_j  NUMERIC(10, 2),
    categorie           VARCHAR(50),
    est_valide          BOOLEAN DEFAULT TRUE,
    score_qualite       NUMERIC(3, 2),
    erreurs_validation  TEXT[],
    date_transformation TIMESTAMP DEFAULT NOW(),
    version_etl         VARCHAR(20) DEFAULT 'v1.0'
);


-- ────────────────────────────────────────────
-- 3. SILVER : Rendements Etages Nettoyes
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS silver.rendements_etage_clean CASCADE;

CREATE TABLE silver.rendements_etage_clean (
    id_silver           BIGSERIAL PRIMARY KEY,
    id_bronze_source    BIGINT,
    id_etage            INTEGER NOT NULL,
    nom_etage           VARCHAR(100),
    annee               INTEGER NOT NULL,
    mois                INTEGER NOT NULL,
    nombre_clients      INTEGER,
    volume_facture_m3   NUMERIC(18, 2),
    volume_amene_m3     NUMERIC(18, 2),
    volume_pertes_m3    NUMERIC(18, 2),
    rendement           NUMERIC(6, 4),
    taux_pertes_pct     NUMERIC(6, 4),
    ilp_m3_jr_km        NUMERIC(10, 4),
    lineaire_km         NUMERIC(12, 3),
    est_valide          BOOLEAN DEFAULT TRUE,
    score_qualite       NUMERIC(3, 2),
    erreurs_validation  TEXT[],
    date_transformation TIMESTAMP DEFAULT NOW(),
    version_etl         VARCHAR(20) DEFAULT 'v1.0'
);


-- ────────────────────────────────────────────
-- 4. SILVER : Capteurs Normalises (INX + PMAC)
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS silver.capteurs_normalises CASCADE;

CREATE TABLE silver.capteurs_normalises (
    id_silver           BIGSERIAL PRIMARY KEY,
    id_bronze_source    BIGINT,
    code_capteur        VARCHAR(20) NOT NULL,
    type_capteur        VARCHAR(10) NOT NULL CHECK (type_capteur IN ('INX', 'PMAC')),
    type_mesure         VARCHAR(20),
    date_mesure         DATE NOT NULL,
    heure_mesure        TIME NOT NULL,
    datetime_source     TIMESTAMP NOT NULL,
    valeur_mesure       NUMERIC(18, 4),
    unite_mesure        VARCHAR(20),
    index_compteur      NUMERIC(18, 6),
    volume_horaire_m3   NUMERIC(18, 4),
    debit_moyen_m3h     NUMERIC(18, 4),
    qualite_donnee      VARCHAR(20) DEFAULT 'VALIDE' 
                        CHECK (qualite_donnee IN ('VALIDE', 'SUSPECT', 'MANQUANT', 'INTERPOLE')),
    est_aberrante       BOOLEAN DEFAULT FALSE,
    date_transformation TIMESTAMP DEFAULT NOW(),
    version_etl         VARCHAR(20) DEFAULT 'v1.0'
);


-- ────────────────────────────────────────────
-- 5. SILVER : Clientele Nettoyee
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS silver.clientele_clean CASCADE;

CREATE TABLE silver.clientele_clean (
    id_silver           BIGSERIAL PRIMARY KEY,
    id_bronze_source    BIGINT,
    num_police          VARCHAR(20) NOT NULL,
    num_compteur        VARCHAR(30),
    num_loc             INTEGER,
    num_sec             INTEGER,
    code_categorie      VARCHAR(5),
    nom_client          VARCHAR(200),
    adresse             VARCHAR(300),
    latitude            NUMERIC(10, 7),
    longitude           NUMERIC(10, 7),
    date_pose_compteur  DATE,
    date_releve_actuel  DATE,
    index_actuel        NUMERIC(18, 2),
    code_anomalie_actuel VARCHAR(5),
    date_releve_precedent DATE,
    index_precedent     NUMERIC(18, 2),
    code_anomalie_precedent VARCHAR(5),
    consommation_m3     NUMERIC(18, 2),
    volume_credite_m3   NUMERIC(18, 2),
    volume_redresse_m3  NUMERIC(18, 2),
    conso_facturee_m3   NUMERIC(18, 2),
    delta_index         NUMERIC(18, 2),
    nb_jours_entre_releves INTEGER,
    conso_journaliere_moy NUMERIC(18, 4),
    est_anomalie        BOOLEAN DEFAULT FALSE,
    est_valide          BOOLEAN DEFAULT TRUE,
    date_transformation TIMESTAMP DEFAULT NOW(),
    version_etl         VARCHAR(20) DEFAULT 'v1.0'
);


-- ────────────────────────────────────────────
-- Verification
-- ────────────────────────────────────────────
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_schema = 'silver' AND table_name = t.table_name) AS nb_colonnes
FROM information_schema.tables t
WHERE table_schema = 'silver'
ORDER BY table_name;