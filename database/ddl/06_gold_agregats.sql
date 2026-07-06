-- ============================================================
-- Fichier : 06_gold_agregats.sql
-- Projet  : SRM Souss-Massa DWH
-- Date    : Juillet 2026
-- ============================================================

-- TODO: Ajouter les instructions SQL ici
-- ============================================================
-- Fichier : 06_gold_agregats.sql
-- Objectif: Tables agregees pour performance Power BI
-- ============================================================

SET search_path TO gold;

-- ────────────────────────────────────────────
-- AGREGAT 1 : Mesures Capteurs par Jour
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.agg_mesures_capteur_jour CASCADE;

CREATE TABLE gold.agg_mesures_capteur_jour (
    id_agg_jour             BIGSERIAL PRIMARY KEY,
    id_capteur              INTEGER NOT NULL REFERENCES gold.dim_capteur(id_capteur),
    id_temps                INTEGER NOT NULL REFERENCES gold.dim_temps(id_temps),
    id_etage                INTEGER REFERENCES gold.dim_etage_pression(id_etage),
    id_type_mesure          INTEGER REFERENCES gold.dim_type_mesure(id_type_mesure),
    -- Debits
    volume_journalier_m3    NUMERIC(18, 4),
    debit_moyen_jour_m3h    NUMERIC(18, 4),
    debit_max_m3h           NUMERIC(18, 4),
    debit_min_m3h           NUMERIC(18, 4),
    dmn_m3h                 NUMERIC(18, 4),
    -- Pression
    pression_moyenne        NUMERIC(10, 2),
    pression_max            NUMERIC(10, 2),
    pression_min            NUMERIC(10, 2),
    -- Index
    index_debut_jour        NUMERIC(18, 6),
    index_fin_jour          NUMERIC(18, 6),
    -- Qualite
    nb_mesures_valides      INTEGER DEFAULT 0,
    nb_mesures_manquantes   INTEGER DEFAULT 0,
    taux_disponibilite_pct  NUMERIC(6, 2),
    date_calcul             TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uk_agg_jour UNIQUE (id_capteur, id_temps, id_type_mesure)
);

COMMENT ON TABLE gold.agg_mesures_capteur_jour IS 
    'Agregat: Mesures capteurs consolidees par jour';


-- ────────────────────────────────────────────
-- AGREGAT 2 : Mesures Capteurs par Mois
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS gold.agg_mesures_capteur_mois CASCADE;

CREATE TABLE gold.agg_mesures_capteur_mois (
    id_agg_mois             BIGSERIAL PRIMARY KEY,
    id_capteur              INTEGER NOT NULL REFERENCES gold.dim_capteur(id_capteur),
    id_temps                INTEGER NOT NULL REFERENCES gold.dim_temps(id_temps),
    id_etage                INTEGER REFERENCES gold.dim_etage_pression(id_etage),
    id_type_mesure          INTEGER REFERENCES gold.dim_type_mesure(id_type_mesure),
    annee                   INTEGER NOT NULL,
    mois                    INTEGER NOT NULL,
    volume_mensuel_m3       NUMERIC(18, 4),
    debit_moyen_mois_m3h    NUMERIC(18, 4),
    dmn_moyen_m3h           NUMERIC(18, 4),
    pression_moyenne_mois   NUMERIC(10, 2),
    nb_jours_avec_donnees   INTEGER DEFAULT 0,
    taux_disponibilite_pct  NUMERIC(6, 2),
    date_calcul             TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uk_agg_mois UNIQUE (id_capteur, annee, mois, id_type_mesure)
);

COMMENT ON TABLE gold.agg_mesures_capteur_mois IS 
    'Agregat: Mesures capteurs consolidees par mois';


-- ────────────────────────────────────────────
-- Verification
-- ────────────────────────────────────────────
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_schema = 'gold' AND table_name = t.table_name) AS nb_colonnes
FROM information_schema.tables t
WHERE table_schema = 'gold' AND table_name LIKE 'agg_%'
ORDER BY table_name;