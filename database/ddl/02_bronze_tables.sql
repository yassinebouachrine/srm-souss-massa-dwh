-- ============================================================
-- Fichier : 02_bronze_tables.sql
-- Projet  : SRM Souss-Massa DWH
-- Date    : Juillet 2026
-- ============================================================

-- TODO: Ajouter les instructions SQL ici
-- ============================================================
-- Fichier : 02_bronze_tables.sql
-- Objectif: 8 tables Bronze (donnees brutes)
-- ============================================================

SET search_path TO bronze;

-- ────────────────────────────────────────────
-- 1. BRONZE : Indicateurs DP (issu de staging)
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS bronze.streamlit_indicateurs_dp CASCADE;

CREATE TABLE bronze.streamlit_indicateurs_dp (
    id_bronze           BIGSERIAL PRIMARY KEY,
    id_saisie_source    INTEGER,
    id_province         INTEGER,
    id_centre           INTEGER,
    code_indicateur     VARCHAR(20),
    annee               INTEGER,
    mois                INTEGER,
    valeur              NUMERIC(18, 4),
    commentaire         TEXT,
    saisi_par           VARCHAR(100),
    date_saisie         TIMESTAMP,
    statut              VARCHAR(20),
    source_type         VARCHAR(30) DEFAULT 'STREAMLIT',
    date_ingestion      TIMESTAMP DEFAULT NOW(),
    fichier_source      VARCHAR(200),
    hash_ligne          VARCHAR(64)
);

COMMENT ON TABLE bronze.streamlit_indicateurs_dp IS 
    'Bronze - Ingestion brute des indicateurs DP';


-- ────────────────────────────────────────────
-- 2. BRONZE : Reclamations DP
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS bronze.streamlit_reclamations_dp CASCADE;

CREATE TABLE bronze.streamlit_reclamations_dp (
    id_bronze           BIGSERIAL PRIMARY KEY,
    id_saisie_source    INTEGER,
    id_province         INTEGER,
    id_centre           INTEGER,
    code_type_reclam    VARCHAR(20),
    annee               INTEGER,
    mois                INTEGER,
    nombre              INTEGER,
    temps_coupure_h     NUMERIC(10, 2),
    delai_traitement_j  NUMERIC(10, 2),
    commentaire         TEXT,
    saisi_par           VARCHAR(100),
    date_saisie         TIMESTAMP,
    statut              VARCHAR(20),
    source_type         VARCHAR(30) DEFAULT 'STREAMLIT',
    date_ingestion      TIMESTAMP DEFAULT NOW(),
    fichier_source      VARCHAR(200),
    hash_ligne          VARCHAR(64)
);


-- ────────────────────────────────────────────
-- 3. BRONZE : Rendements Etages
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS bronze.streamlit_rendements_etage CASCADE;

CREATE TABLE bronze.streamlit_rendements_etage (
    id_bronze           BIGSERIAL PRIMARY KEY,
    id_saisie_source    INTEGER,
    id_etage            INTEGER,
    annee               INTEGER,
    mois                INTEGER,
    nombre_clients      INTEGER,
    volume_facture_m3   NUMERIC(18, 2),
    volume_amene_m3     NUMERIC(18, 2),
    rendement           NUMERIC(6, 4),
    saisi_par           VARCHAR(100),
    date_saisie         TIMESTAMP,
    statut              VARCHAR(20),
    source_type         VARCHAR(30) DEFAULT 'STREAMLIT',
    date_ingestion      TIMESTAMP DEFAULT NOW(),
    fichier_source      VARCHAR(200),
    hash_ligne          VARCHAR(64)
);


-- ────────────────────────────────────────────
-- 4. BRONZE : Volumes Amenes
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS bronze.streamlit_volumes_amenes CASCADE;

CREATE TABLE bronze.streamlit_volumes_amenes (
    id_bronze           BIGSERIAL PRIMARY KEY,
    id_saisie_source    INTEGER,
    id_etage            INTEGER,
    annee               INTEGER,
    mois                INTEGER,
    volume_m3           NUMERIC(18, 2),
    saisi_par           VARCHAR(100),
    date_saisie         TIMESTAMP,
    statut              VARCHAR(20),
    source_type         VARCHAR(30) DEFAULT 'STREAMLIT',
    date_ingestion      TIMESTAMP DEFAULT NOW(),
    fichier_source      VARCHAR(200),
    hash_ligne          VARCHAR(64)
);


-- ────────────────────────────────────────────
-- 5. BRONZE : Capteurs INX (CSV)
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS bronze.capteurs_inx CASCADE;

CREATE TABLE bronze.capteurs_inx (
    id_bronze           BIGSERIAL PRIMARY KEY,
    code_capteur        VARCHAR(20),
    datetime_source     TIMESTAMP,
    date_mesure         DATE,
    heure_mesure        TIME,
    index_compteur      NUMERIC(18, 6),
    source_type         VARCHAR(30) DEFAULT 'CAPTEUR_INX',
    fichier_source      VARCHAR(200),
    date_ingestion      TIMESTAMP DEFAULT NOW(),
    hash_ligne          VARCHAR(64),
    est_valide          BOOLEAN DEFAULT TRUE,
    message_erreur      TEXT
);

COMMENT ON TABLE bronze.capteurs_inx IS 
    'Bronze - Capteurs INX (CSV convertis quotidiennement)';


-- ────────────────────────────────────────────
-- 6. BRONZE : Capteurs PMAC Multi-Types
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS bronze.capteurs_pmac CASCADE;

CREATE TABLE bronze.capteurs_pmac (
    id_bronze           BIGSERIAL PRIMARY KEY,
    -- Metadonnees PMAC
    site_name           VARCHAR(100),
    pmac_id             INTEGER,
    channel_no          INTEGER,
    code_capteur        VARCHAR(20),
    -- Type de mesure
    type_mesure         VARCHAR(20),
    colonne_valeur      VARCHAR(30),
    -- Donnees
    datetime_source     TIMESTAMP,
    date_mesure         DATE,
    heure_mesure        TIME,
    valeur_mesure       NUMERIC(18, 4),
    debit_cum_hr        NUMERIC(18, 4),
    unite               VARCHAR(20),
    -- Metadonnees
    source_type         VARCHAR(30) DEFAULT 'CAPTEUR_PMAC',
    fichier_source      VARCHAR(200),
    date_ingestion      TIMESTAMP DEFAULT NOW(),
    hash_ligne          VARCHAR(64),
    est_valide          BOOLEAN DEFAULT TRUE,
    message_erreur      TEXT
);

COMMENT ON TABLE bronze.capteurs_pmac IS 
    'Bronze - Capteurs PMAC multi-types (DEBIT/PRESSION/INDEX/AMOUNT)';


-- ────────────────────────────────────────────
-- 7. BRONZE : Alarmes Capteurs (ALM)
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS bronze.capteurs_alarmes CASCADE;

CREATE TABLE bronze.capteurs_alarmes (
    id_bronze           BIGSERIAL PRIMARY KEY,
    code_capteur        VARCHAR(20),
    site_name           VARCHAR(100),
    pmac_id             INTEGER,
    datetime_alarme     TIMESTAMP,
    type_alarme         VARCHAR(50),
    code_alarme         VARCHAR(20),
    message_alarme      TEXT,
    severite            VARCHAR(20),
    est_acquittee       BOOLEAN DEFAULT FALSE,
    date_acquittement   TIMESTAMP,
    acquittee_par       VARCHAR(100),
    fichier_source      VARCHAR(200),
    date_ingestion      TIMESTAMP DEFAULT NOW(),
    hash_ligne          VARCHAR(64)
);

COMMENT ON TABLE bronze.capteurs_alarmes IS 
    'Bronze - Alarmes capteurs (fichiers ALM)';


-- ────────────────────────────────────────────
-- 8. BRONZE : Clientele Gstcom
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS bronze.clientele_gstcom CASCADE;

CREATE TABLE bronze.clientele_gstcom (
    id_bronze           BIGSERIAL PRIMARY KEY,
    type_part_a_dm      INTEGER,
    loc                 INTEGER,
    sec                 INTEGER,
    trn                 INTEGER,
    ord                 INTEGER,
    cat                 VARCHAR(5),
    police              VARCHAR(20),
    conso               NUMERIC(18, 2),
    credites            NUMERIC(18, 2),
    redres              NUMERIC(18, 2),
    conso_facture       NUMERIC(18, 2),
    dt_rlv02            DATE,
    hr_rlv02            TIME,
    an_02               VARCHAR(5),
    idx_02              NUMERIC(18, 2),
    dt_rlv01            DATE,
    hr_rlv01            TIME,
    an_01               VARCHAR(5),
    idx_01              NUMERIC(18, 2),
    latitude            NUMERIC(10, 7),
    longitude           NUMERIC(10, 7),
    mle_lecteur         VARCHAR(30),
    nom                 VARCHAR(200),
    adresse             VARCHAR(300),
    dt_pose             DATE,
    num_cpt             VARCHAR(30),
    source_type         VARCHAR(30) DEFAULT 'GSTCOM',
    fichier_source      VARCHAR(200),
    date_ingestion      TIMESTAMP DEFAULT NOW(),
    hash_ligne          VARCHAR(64),
    est_valide          BOOLEAN DEFAULT TRUE,
    message_erreur      TEXT
);

COMMENT ON TABLE bronze.clientele_gstcom IS 
    'Bronze - Fichier clientele Gstcom';


-- ────────────────────────────────────────────
-- Verification
-- ────────────────────────────────────────────
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_schema = 'bronze' AND table_name = t.table_name) AS nb_colonnes
FROM information_schema.tables t
WHERE table_schema = 'bronze'
ORDER BY table_name;