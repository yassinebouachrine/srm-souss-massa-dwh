-- ============================================================
-- Fichier : 05_gold_faits.sql
-- Projet  : SRM Souss-Massa DWH
-- Date    : Juillet 2026
-- ============================================================

-- TODO: Ajouter les instructions SQL ici
-- ============================================================
-- Fichier : 05_gold_faits.sql
-- Objectif: 5 tables de faits (schema constellation)
-- ============================================================

SET search_path TO gold;

-- ────────────────────────────────────────────
-- FAIT 1 : Indicateurs de Performance DP
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.fait_indicateurs_performance_dp CASCADE;

CREATE TABLE gold.fait_indicateurs_performance_dp (
    id_fait_indicateur      BIGSERIAL PRIMARY KEY,
    id_temps                INTEGER NOT NULL REFERENCES gold.dim_temps(id_temps),
    id_province             INTEGER NOT NULL REFERENCES gold.dim_province(id_province),
    id_centre               INTEGER REFERENCES gold.dim_centre(id_centre),
    id_type_indicateur      INTEGER NOT NULL REFERENCES gold.dim_type_indicateur_dp(id_type_indicateur),
    valeur_mensuelle        NUMERIC(18, 4),
    valeur_recapitulatif    NUMERIC(18, 4),
    fichier_source          VARCHAR(200),
    onglet_source           VARCHAR(100),
    date_chargement         TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uk_fait_indicateurs 
        UNIQUE (id_temps, id_province, id_centre, id_type_indicateur)
);

COMMENT ON TABLE gold.fait_indicateurs_performance_dp IS 
    'Faits: Indicateurs performance mensuels';


-- ────────────────────────────────────────────
-- FAIT 2 : Reclamations DP
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.fait_reclamations_dp CASCADE;

CREATE TABLE gold.fait_reclamations_dp (
    id_fait_reclamation     BIGSERIAL PRIMARY KEY,
    id_temps                INTEGER NOT NULL REFERENCES gold.dim_temps(id_temps),
    id_province             INTEGER NOT NULL REFERENCES gold.dim_province(id_province),
    id_centre               INTEGER REFERENCES gold.dim_centre(id_centre),
    id_type_reclamation     INTEGER NOT NULL REFERENCES gold.dim_type_reclamation(id_type_reclamation),
    nombre_reclamations     INTEGER DEFAULT 0,
    temps_moyen_coupure_h   NUMERIC(10, 2),
    delai_moyen_traitement_j NUMERIC(10, 2),
    valeur_brute            NUMERIC(18, 4),
    fichier_source          VARCHAR(200),
    onglet_source           VARCHAR(100),
    date_chargement         TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uk_fait_reclamations 
        UNIQUE (id_temps, id_province, id_centre, id_type_reclamation)
);

COMMENT ON TABLE gold.fait_reclamations_dp IS 
    'Faits: Reclamations mensuelles par type';


-- ────────────────────────────────────────────
-- FAIT 3 : Rendement par Etage
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.fait_rendement_etage CASCADE;

CREATE TABLE gold.fait_rendement_etage (
    id_fait_rendement       BIGSERIAL PRIMARY KEY,
    id_temps                INTEGER NOT NULL REFERENCES gold.dim_temps(id_temps),
    id_etage                INTEGER NOT NULL REFERENCES gold.dim_etage_pression(id_etage),
    nombre_clients          INTEGER,
    volume_facture_m3       NUMERIC(18, 2),
    volume_amene_m3         NUMERIC(18, 2),
    volume_pertes_m3        NUMERIC(18, 2),
    rendement               NUMERIC(6, 4),
    ilp_m3_jr_km            NUMERIC(10, 4),
    lineaire_km_snapshot    NUMERIC(12, 3),
    nb_jours_mois           INTEGER,
    consommation_moy_client NUMERIC(18, 4),
    taux_pertes_pct         NUMERIC(6, 4),
    date_chargement         TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uk_fait_rendement 
        UNIQUE (id_temps, id_etage)
);

COMMENT ON TABLE gold.fait_rendement_etage IS 
    'Faits: Rendement mensuel par etage';


-- ────────────────────────────────────────────
-- FAIT 4 : Consommation Client
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.fait_consommation_client CASCADE;

CREATE TABLE gold.fait_consommation_client (
    id_fait_consommation    BIGSERIAL PRIMARY KEY,
    id_client               BIGINT NOT NULL REFERENCES gold.dim_client(id_client),
    id_temps                INTEGER NOT NULL REFERENCES gold.dim_temps(id_temps),
    id_localite             INTEGER REFERENCES gold.dim_localite(id_localite),
    id_secteur              INTEGER REFERENCES gold.dim_secteur_hydraulique(id_secteur),
    id_etage                INTEGER REFERENCES gold.dim_etage_pression(id_etage),
    id_centre               INTEGER REFERENCES gold.dim_centre(id_centre),
    id_province             INTEGER REFERENCES gold.dim_province(id_province),
    id_anomalie_actuel      INTEGER REFERENCES gold.dim_anomalie_releve(id_anomalie),
    id_anomalie_precedent   INTEGER REFERENCES gold.dim_anomalie_releve(id_anomalie),
    id_categorie            INTEGER REFERENCES gold.dim_categorie_client(id_categorie),
    consommation_m3         NUMERIC(18, 2),
    volume_credite_m3       NUMERIC(18, 2),
    volume_redresse_m3      NUMERIC(18, 2),
    conso_facturee_m3       NUMERIC(18, 2),
    date_releve_actuel      DATE,
    heure_releve_actuel     VARCHAR(10),
    code_anomalie_actuel    VARCHAR(5),
    index_actuel            NUMERIC(18, 2),
    date_releve_precedent   DATE,
    heure_releve_precedent  VARCHAR(10),
    code_anomalie_precedent VARCHAR(5),
    index_precedent         NUMERIC(18, 2),
    delta_index             NUMERIC(18, 2),
    nb_jours_entre_releves  INTEGER,
    conso_journaliere_moy   NUMERIC(18, 4),
    est_anomalie            BOOLEAN DEFAULT FALSE,
    trn_source              INTEGER,
    ord_source              INTEGER,
    date_chargement         TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE gold.fait_consommation_client IS 
    'Faits: Consommation par client';


-- ────────────────────────────────────────────
-- FAIT 5 : Mesures Capteurs Multi-Types
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.fait_mesures_capteur CASCADE;

CREATE TABLE gold.fait_mesures_capteur (
    id_fait_mesure          BIGSERIAL PRIMARY KEY,
    id_capteur              INTEGER NOT NULL REFERENCES gold.dim_capteur(id_capteur),
    id_temps                INTEGER NOT NULL REFERENCES gold.dim_temps(id_temps),
    id_heure                INTEGER NOT NULL REFERENCES gold.dim_heure(id_heure),
    id_etage                INTEGER REFERENCES gold.dim_etage_pression(id_etage),
    id_secteur              INTEGER REFERENCES gold.dim_secteur_hydraulique(id_secteur),
    id_type_mesure          INTEGER REFERENCES gold.dim_type_mesure(id_type_mesure),
    id_canal_mapping        INTEGER REFERENCES gold.dim_canal_mapping(id_canal),
    datetime_source         TIMESTAMP,
    valeur_mesure           NUMERIC(18, 4),
    unite_mesure            VARCHAR(20),
    numero_channel          INTEGER,
    index_compteur_m3       NUMERIC(18, 6),
    debit_cum_hr            NUMERIC(18, 4),
    volume_horaire_m3       NUMERIC(18, 4),
    index_precedent_m3      NUMERIC(18, 6),
    debit_moyen_m3_h        NUMERIC(18, 4),
    qualite_donnee          VARCHAR(20) DEFAULT 'VALIDE',
    est_valeur_manquante    BOOLEAN DEFAULT FALSE,
    est_valeur_aberrante    BOOLEAN DEFAULT FALSE,
    type_capteur_source     VARCHAR(10),
    fichier_source          VARCHAR(50),
    date_chargement         TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uk_fait_mesures 
        UNIQUE (id_capteur, id_temps, id_heure, id_type_mesure)
);

COMMENT ON TABLE gold.fait_mesures_capteur IS 
    'Faits: Mesures capteurs multi-types (grain horaire)';


-- ────────────────────────────────────────────
-- Verification
-- ────────────────────────────────────────────
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_schema = 'gold' AND table_name = t.table_name) AS nb_colonnes
FROM information_schema.tables t
WHERE table_schema = 'gold' AND table_name LIKE 'fait_%'
ORDER BY table_name;