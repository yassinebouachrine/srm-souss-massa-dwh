-- ============================================================
-- Fichier : 04_gold_dimensions.sql
-- Projet  : SRM Souss-Massa DWH
-- Date    : Juillet 2026
-- ============================================================

-- TODO: Ajouter les instructions SQL ici
-- ============================================================
-- Fichier : 04_gold_dimensions.sql
-- Objectif: 17 dimensions du Data Warehouse
--   14 dimensions classiques + 3 nouvelles pour capteurs
-- ============================================================

SET search_path TO gold;

-- ────────────────────────────────────────────
-- 1. DIM_TEMPS (partagee par tous les faits)
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.dim_temps CASCADE;

CREATE TABLE gold.dim_temps (
    id_temps            INTEGER PRIMARY KEY,
    date_complete       DATE NOT NULL UNIQUE,
    jour                INTEGER NOT NULL,
    jour_semaine        INTEGER NOT NULL,
    nom_jour            VARCHAR(15),
    semaine_annee       INTEGER,
    mois                INTEGER NOT NULL,
    nom_mois            VARCHAR(15),
    mois_annee          VARCHAR(10),
    trimestre           INTEGER NOT NULL,
    nom_trimestre       VARCHAR(5),
    semestre            INTEGER,
    annee               INTEGER NOT NULL,
    saison              VARCHAR(15),
    est_weekend         BOOLEAN,
    est_jour_ferie      BOOLEAN,
    est_fin_mois        BOOLEAN,
    nb_jours_dans_mois  INTEGER
);

COMMENT ON TABLE gold.dim_temps IS 'Dimension temporelle (grain jour)';


-- ────────────────────────────────────────────
-- 2. DIM_HEURE (pour capteurs)
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.dim_heure CASCADE;

CREATE TABLE gold.dim_heure (
    id_heure            INTEGER PRIMARY KEY,
    heure               INTEGER NOT NULL CHECK (heure BETWEEN 0 AND 23),
    minute              INTEGER DEFAULT 0,
    heure_minute        VARCHAR(5),
    tranche_horaire     VARCHAR(20),
    periode_journee     VARCHAR(20),
    est_heure_pointe    BOOLEAN DEFAULT FALSE,
    est_heure_nuit      BOOLEAN DEFAULT FALSE
);

COMMENT ON TABLE gold.dim_heure IS 'Dimension heure (granularite horaire capteurs)';


-- ────────────────────────────────────────────
-- 3. DIM_REGION
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.dim_region CASCADE;

CREATE TABLE gold.dim_region (
    id_region           SERIAL PRIMARY KEY,
    code_region         VARCHAR(10) UNIQUE NOT NULL,
    nom_region          VARCHAR(50) NOT NULL,
    pays                VARCHAR(30) DEFAULT 'Maroc'
);

COMMENT ON TABLE gold.dim_region IS 'Dimension region';


-- ────────────────────────────────────────────
-- 4. DIM_PROVINCE
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.dim_province CASCADE;

CREATE TABLE gold.dim_province (
    id_province         SERIAL PRIMARY KEY,
    code_province       VARCHAR(10) UNIQUE NOT NULL,
    nom_province        VARCHAR(100) NOT NULL,
    id_region           INTEGER REFERENCES gold.dim_region(id_region)
);

COMMENT ON TABLE gold.dim_province IS 'Dimension province (6 provinces Souss-Massa)';


-- ────────────────────────────────────────────
-- 5. DIM_CENTRE
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.dim_centre CASCADE;

CREATE TABLE gold.dim_centre (
    id_centre           SERIAL PRIMARY KEY,
    code_centre         VARCHAR(20) UNIQUE NOT NULL,
    nom_centre          VARCHAR(100) NOT NULL,
    type_centre         VARCHAR(30),
    id_province         INTEGER REFERENCES gold.dim_province(id_province)
);

COMMENT ON TABLE gold.dim_centre IS 'Dimension centre/commune';


-- ────────────────────────────────────────────
-- 6. DIM_ETAGE_PRESSION
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.dim_etage_pression CASCADE;

CREATE TABLE gold.dim_etage_pression (
    id_etage            SERIAL PRIMARY KEY,
    code_etage          VARCHAR(20) UNIQUE NOT NULL,
    nom_etage           VARCHAR(100) NOT NULL,
    cote_pression       INTEGER,
    lineaire_km         NUMERIC(12, 3),
    lineaire_m          NUMERIC(15, 2),
    nombre_secteurs     INTEGER DEFAULT 0,
    id_province         INTEGER REFERENCES gold.dim_province(id_province),
    id_centre           INTEGER REFERENCES gold.dim_centre(id_centre),
    date_creation       TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE gold.dim_etage_pression IS 'Dimension etages de pression hydraulique';


-- ────────────────────────────────────────────
-- 7. DIM_SECTEUR_HYDRAULIQUE
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.dim_secteur_hydraulique CASCADE;

CREATE TABLE gold.dim_secteur_hydraulique (
    id_secteur          SERIAL PRIMARY KEY,
    code_secteur        VARCHAR(20) UNIQUE NOT NULL,
    nom_secteur         VARCHAR(100) NOT NULL,
    lineaire_m          NUMERIC(15, 2),
    lineaire_km         NUMERIC(12, 3),
    id_etage            INTEGER REFERENCES gold.dim_etage_pression(id_etage),
    date_creation       TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE gold.dim_secteur_hydraulique IS 'Dimension secteurs hydrauliques';


-- ────────────────────────────────────────────
-- 8. DIM_LOCALITE
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.dim_localite CASCADE;

CREATE TABLE gold.dim_localite (
    id_localite         SERIAL PRIMARY KEY,
    id_seq_source       INTEGER,
    num_loc             INTEGER NOT NULL,
    num_sec             INTEGER NOT NULL,
    code_etage_num      INTEGER,
    code_loc_sec        VARCHAR(20),
    nom_etage_rattache  VARCHAR(100),
    id_secteur          INTEGER REFERENCES gold.dim_secteur_hydraulique(id_secteur),
    id_etage            INTEGER REFERENCES gold.dim_etage_pression(id_etage),
    date_creation       TIMESTAMP DEFAULT NOW(),
    UNIQUE (num_loc, num_sec, code_etage_num)
);

COMMENT ON TABLE gold.dim_localite IS 'Dimension localites (matrice affectation)';


-- ────────────────────────────────────────────
-- 9. NOUVELLE : DIM_GROUPE_MESURE
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.dim_groupe_mesure CASCADE;

CREATE TABLE gold.dim_groupe_mesure (
    id_groupe_mesure    SERIAL PRIMARY KEY,
    code_groupe         VARCHAR(30) UNIQUE NOT NULL,
    libelle_groupe      VARCHAR(100) NOT NULL,
    description         VARCHAR(300),
    ordre_affichage     INTEGER
);

COMMENT ON TABLE gold.dim_groupe_mesure IS 
    'Groupes de mesure (Secteurs, Gros Conso, Modulateurs, Reservoirs)';


-- ────────────────────────────────────────────
-- 10. NOUVELLE : DIM_TYPE_MESURE
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.dim_type_mesure CASCADE;

CREATE TABLE gold.dim_type_mesure (
    id_type_mesure      SERIAL PRIMARY KEY,
    code_type           VARCHAR(20) UNIQUE NOT NULL,
    libelle_type        VARCHAR(50) NOT NULL,
    unite_defaut        VARCHAR(20),
    description         VARCHAR(300)
);

COMMENT ON TABLE gold.dim_type_mesure IS 
    'Types de mesures (DEBIT, PRESSION, INDEX, AMOUNT, NIVEAU, ALARM)';


-- ────────────────────────────────────────────
-- 11. DIM_CAPTEUR (avec toutes les colonnes)
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.dim_capteur CASCADE;

CREATE TABLE gold.dim_capteur (
    id_capteur          SERIAL PRIMARY KEY,
    code_capteur        VARCHAR(20) UNIQUE NOT NULL,
    nom_fichier_source  VARCHAR(50),
    type_capteur        VARCHAR(10) NOT NULL CHECK (type_capteur IN ('INX', 'PMAC')),
    site_name           VARCHAR(100),
    pmac_id             INTEGER,
    channel_no          INTEGER,
    unite_mesure        VARCHAR(20),
    format_source       VARCHAR(20),
    latitude            NUMERIC(10, 7),
    longitude           NUMERIC(10, 7),
    date_installation   DATE,
    statut              VARCHAR(15) DEFAULT 'ACTIF' 
                        CHECK (statut IN ('ACTIF', 'INACTIF', 'EN_PANNE')),
    -- Colonnes referentiels capteurs
    station_id          INTEGER,
    nom_station         VARCHAR(200),
    point_de_mesure     VARCHAR(200),
    id_groupe_mesure    INTEGER REFERENCES gold.dim_groupe_mesure(id_groupe_mesure),
    est_modulateur      BOOLEAN DEFAULT FALSE,
    est_point_pression  BOOLEAN DEFAULT FALSE,
    est_debit           BOOLEAN DEFAULT FALSE,
    est_gros_conso      BOOLEAN DEFAULT FALSE,
    est_reservoir       BOOLEAN DEFAULT FALSE,
    -- References geo
    id_etage            INTEGER REFERENCES gold.dim_etage_pression(id_etage),
    id_secteur          INTEGER REFERENCES gold.dim_secteur_hydraulique(id_secteur),
    date_creation       TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE gold.dim_capteur IS 
    'Dimension capteurs multi-types avec classification';


-- ────────────────────────────────────────────
-- 12. NOUVELLE : DIM_CANAL_MAPPING
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.dim_canal_mapping CASCADE;

CREATE TABLE gold.dim_canal_mapping (
    id_canal            SERIAL PRIMARY KEY,
    key_canal           VARCHAR(50) UNIQUE NOT NULL,
    canal_label         VARCHAR(200) NOT NULL,
    code_capteur        VARCHAR(20),
    code_channel        VARCHAR(20),
    type_mesure         VARCHAR(20),
    numero_channel      INTEGER,
    fonction_metier     VARCHAR(100),
    element_reseau      VARCHAR(100),
    id_capteur          INTEGER REFERENCES gold.dim_capteur(id_capteur),
    id_type_mesure      INTEGER REFERENCES gold.dim_type_mesure(id_type_mesure),
    date_creation       TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE gold.dim_canal_mapping IS 
    'Mapping technique -> metier des canaux PMAC';


-- ────────────────────────────────────────────
-- 13. DIM_CLIENT
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.dim_client CASCADE;

CREATE TABLE gold.dim_client (
    id_client           BIGSERIAL PRIMARY KEY,
    num_police          VARCHAR(20) UNIQUE NOT NULL,
    type_part_a_dm      INTEGER,
    num_loc             INTEGER,
    num_sec             INTEGER,
    trn                 INTEGER,
    ord                 INTEGER,
    cat                 VARCHAR(5),
    nom_client          VARCHAR(200),
    adresse             VARCHAR(300),
    latitude            NUMERIC(10, 7),
    longitude           NUMERIC(10, 7),
    code_lecteur        VARCHAR(30),
    num_compteur        VARCHAR(30),
    date_pose_compteur  DATE,
    date_premiere_releve DATE,
    est_actif           BOOLEAN DEFAULT TRUE,
    id_localite         INTEGER REFERENCES gold.dim_localite(id_localite),
    id_secteur          INTEGER REFERENCES gold.dim_secteur_hydraulique(id_secteur),
    id_etage            INTEGER REFERENCES gold.dim_etage_pression(id_etage),
    id_centre           INTEGER REFERENCES gold.dim_centre(id_centre),
    id_province         INTEGER REFERENCES gold.dim_province(id_province),
    date_creation       TIMESTAMP DEFAULT NOW(),
    date_modification   TIMESTAMP
);

COMMENT ON TABLE gold.dim_client IS 'Dimension clients (fichier Gstcom)';


-- ────────────────────────────────────────────
-- 14. DIM_TYPE_INDICATEUR_DP
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.dim_type_indicateur_dp CASCADE;

CREATE TABLE gold.dim_type_indicateur_dp (
    id_type_indicateur  SERIAL PRIMARY KEY,
    code_indicateur     VARCHAR(20) UNIQUE NOT NULL,
    libelle_indicateur  VARCHAR(100) NOT NULL,
    unite               VARCHAR(20),
    categorie           VARCHAR(50),
    sous_categorie      VARCHAR(50),
    ligne_source_excel  INTEGER,
    est_calculable      BOOLEAN DEFAULT FALSE,
    formule_calcul      VARCHAR(200),
    ordre_affichage     INTEGER
);

COMMENT ON TABLE gold.dim_type_indicateur_dp IS 
    'Dimension types indicateurs DP (21 indicateurs)';


-- ────────────────────────────────────────────
-- 15. DIM_TYPE_RECLAMATION
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.dim_type_reclamation CASCADE;

CREATE TABLE gold.dim_type_reclamation (
    id_type_reclamation SERIAL PRIMARY KEY,
    code_type           VARCHAR(20) UNIQUE NOT NULL,
    libelle_reclamation VARCHAR(100) NOT NULL,
    categorie_reclamation VARCHAR(50),
    ligne_source_excel  INTEGER,
    est_comptage        BOOLEAN DEFAULT TRUE,
    est_duree           BOOLEAN DEFAULT FALSE,
    ordre_affichage     INTEGER
);

COMMENT ON TABLE gold.dim_type_reclamation IS 
    'Dimension types reclamations (10 types)';


-- ────────────────────────────────────────────
-- 16. DIM_ANOMALIE_RELEVE
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.dim_anomalie_releve CASCADE;

CREATE TABLE gold.dim_anomalie_releve (
    id_anomalie         SERIAL PRIMARY KEY,
    code_anomalie       VARCHAR(5) UNIQUE NOT NULL,
    libelle_anomalie    VARCHAR(100) NOT NULL,
    description         VARCHAR(300),
    est_normal          BOOLEAN DEFAULT FALSE
);

COMMENT ON TABLE gold.dim_anomalie_releve IS 
    'Codes anomalies releves (N, A, I, K)';


-- ────────────────────────────────────────────
-- 17. DIM_CATEGORIE_CLIENT
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.dim_categorie_client CASCADE;

CREATE TABLE gold.dim_categorie_client (
    id_categorie        SERIAL PRIMARY KEY,
    code_categorie      VARCHAR(5) UNIQUE NOT NULL,
    libelle_categorie   VARCHAR(100) NOT NULL,
    description         VARCHAR(300)
);

COMMENT ON TABLE gold.dim_categorie_client IS 
    'Categories clients (A, G, B, D, P)';


-- ────────────────────────────────────────────
-- Verification
-- ────────────────────────────────────────────
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_schema = 'gold' AND table_name = t.table_name) AS nb_colonnes
FROM information_schema.tables t
WHERE table_schema = 'gold' AND table_name LIKE 'dim_%'
ORDER BY table_name;