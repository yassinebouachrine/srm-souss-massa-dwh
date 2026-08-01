-- ═══════════════════════════════════════════════════════════════
-- DWH — ÉTOILE B : Faits Mesures Capteurs
--
-- 3 tables de faits pour granularités différentes :
--   1. fait_mesure_temps_reel   : mesures fines (10min, 15min, instantané)
--   2. fait_mesure_journaliere  : agrégats journaliers (min/moy/max)
--   3. fait_bilan_periode       : bilans début/fin de période (mensuel)
--
-- ⚠️ Conforme au schéma constellation :
--   • Chaque fait référence DIM_ETAGE et DIM_SECTEUR (transversales)
--   • Utilise id_etage=0 et id_secteur=0 si non applicable (sentinel)
-- ═══════════════════════════════════════════════════════════════


-- ─────────────────────────────────────────────────────────────
-- FAIT_MESURE_TEMPS_REEL
-- Granularité : 1 mesure = 1 point × 1 datetime × 1 voie
--
-- Volumétrie estimée :
--   - PMAC : ~150 points × 144 mesures/jour = ~21 600 lignes/jour
--   - Sur 1 an : ~7,9 millions de lignes → penser au partitionnement (phase 2)
-- ─────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dwh.fait_mesure_temps_reel CASCADE;
CREATE TABLE dwh.fait_mesure_temps_reel (
    id_fait                 BIGSERIAL PRIMARY KEY,
    
    -- ─── Clés de dimension ───
    id_temps                INTEGER NOT NULL REFERENCES dwh.dim_temps(id_temps),
    id_etage                INTEGER NOT NULL DEFAULT 0 REFERENCES dwh.dim_etage(id_etage),
    id_secteur              INTEGER NOT NULL DEFAULT 0 REFERENCES dwh.dim_secteur(id_secteur),
    id_point_mesure         INTEGER NOT NULL REFERENCES dwh.dim_point_mesure(id_point_mesure),
    id_source_mesure        INTEGER NOT NULL REFERENCES dwh.dim_source_mesure(id_source_mesure),
    
    -- ─── Timestamp précis ───
    heure                   TIMESTAMP NOT NULL,
    
    -- ─── Mesures ───
    index_compteur          DOUBLE PRECISION,
    pression_bar            DOUBLE PRECISION,
    pression_amont_bar      DOUBLE PRECISION,
    pression_aval_bar       DOUBLE PRECISION,
    debit_m3_h              DOUBLE PRECISION,
    volume_15min            DOUBLE PRECISION,
    qualite_donnees         VARCHAR(20) DEFAULT 'GOOD',
    
    -- ─── Métadonnées techniques ───
    voie                    VARCHAR(20) NOT NULL,         -- PRESSION | DEBIT | INDEX | VOLUME
    canal                   VARCHAR(50) NOT NULL,         -- ← AJOUTÉ : "PRESSION_01", "DEBIT_02", "INDEX_03"
    unite                   VARCHAR(20),
    fichier_source          VARCHAR(255),
    canal_source            VARCHAR(50),
    date_chargement         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- ─── Contrainte unique CORRIGÉE ───
    CONSTRAINT uq_fait_tr UNIQUE (id_point_mesure, heure, voie, canal)
);

-- Index (inchangés + 1 nouveau)
CREATE INDEX idx_fait_tr_temps     ON dwh.fait_mesure_temps_reel(id_temps);
CREATE INDEX idx_fait_tr_etage     ON dwh.fait_mesure_temps_reel(id_etage);
CREATE INDEX idx_fait_tr_secteur   ON dwh.fait_mesure_temps_reel(id_secteur);
CREATE INDEX idx_fait_tr_point     ON dwh.fait_mesure_temps_reel(id_point_mesure);
CREATE INDEX idx_fait_tr_source    ON dwh.fait_mesure_temps_reel(id_source_mesure);
CREATE INDEX idx_fait_tr_heure     ON dwh.fait_mesure_temps_reel(heure);
CREATE INDEX idx_fait_tr_voie      ON dwh.fait_mesure_temps_reel(voie);
CREATE INDEX idx_fait_tr_canal     ON dwh.fait_mesure_temps_reel(canal);   -- ← NOUVEAU
CREATE INDEX idx_fait_tr_qualite   ON dwh.fait_mesure_temps_reel(qualite_donnees) 
                                    WHERE qualite_donnees != 'GOOD';

                                    
COMMENT ON TABLE dwh.fait_mesure_temps_reel IS 
    'Mesures capteurs granularité fine (10min/15min/instantané) — PMAC + PCWIN';
COMMENT ON COLUMN dwh.fait_mesure_temps_reel.id_etage IS 
    'FK vers dim_etage. Utiliser id=0 (INCONNU) si point non rattaché à un étage';
COMMENT ON COLUMN dwh.fait_mesure_temps_reel.id_secteur IS 
    'FK vers dim_secteur. Utiliser id=0 (INCONNU) si point non rattaché à un secteur';
COMMENT ON COLUMN dwh.fait_mesure_temps_reel.qualite_donnees IS 
    'GOOD (valide), SUSPECT (valeur limite/nulle), BAD (aberrante rejetée)';
COMMENT ON COLUMN dwh.fait_mesure_temps_reel.voie IS 
    'Type de mesure : PRESSION, DEBIT, INDEX, VOLUME (route vers la bonne colonne)';


-- ─────────────────────────────────────────────────────────────
-- FAIT_MESURE_JOURNALIERE
-- Granularité : 1 ligne = 1 point × 1 jour × 1 voie
-- Calculé par agrégation depuis fait_mesure_temps_reel
-- ─────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dwh.fait_mesure_journaliere CASCADE;
CREATE TABLE dwh.fait_mesure_journaliere (
    id_fait                 BIGSERIAL PRIMARY KEY,
    
    -- ─── Clés de dimension ───
    id_temps                INTEGER NOT NULL 
                            REFERENCES dwh.dim_temps(id_temps),
    id_etage                INTEGER NOT NULL DEFAULT 0
                            REFERENCES dwh.dim_etage(id_etage),
    id_secteur              INTEGER NOT NULL DEFAULT 0
                            REFERENCES dwh.dim_secteur(id_secteur),
    id_point_mesure         INTEGER NOT NULL 
                            REFERENCES dwh.dim_point_mesure(id_point_mesure),
    id_source_mesure        INTEGER NOT NULL 
                            REFERENCES dwh.dim_source_mesure(id_source_mesure),
    
    -- ─── Mesures du schéma constellation ───
    index_08h               DOUBLE PRECISION,             -- Index à 08h (référence journalière)
    index_08h_j_plus1       DOUBLE PRECISION,             -- Index à 08h du lendemain
    volume_journalier_m3    DOUBLE PRECISION,             -- Volume calculé du jour
    debit_min_jour          DOUBLE PRECISION,
    debit_moy_jour          DOUBLE PRECISION,
    debit_max_jour          DOUBLE PRECISION,
    pct_min_sur_moy         DOUBLE PRECISION,             -- (débit_min / débit_moy) * 100
    pression_amont_moy      DOUBLE PRECISION,
    pression_aval_moy       DOUBLE PRECISION,
    pression_min            DOUBLE PRECISION,
    pression_max            DOUBLE PRECISION,
    nb_mesures_valides      INTEGER DEFAULT 0,
    qualite_donnees_jour    VARCHAR(20) DEFAULT 'GOOD',
    
    -- ─── Métadonnées techniques (extras) ───
    voie                    VARCHAR(20) NOT NULL,         -- PRESSION|DEBIT|INDEX
    nb_mesures_attendues    INTEGER DEFAULT 144,          -- 144 mesures/jour à 10min
    taux_completude         DECIMAL(5, 2),                -- (nb_valides / nb_attendues) * 100
    date_calcul             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_fait_jour UNIQUE (id_point_mesure, id_temps, voie)
);

CREATE INDEX idx_fait_jour_temps   ON dwh.fait_mesure_journaliere(id_temps);
CREATE INDEX idx_fait_jour_etage   ON dwh.fait_mesure_journaliere(id_etage);
CREATE INDEX idx_fait_jour_secteur ON dwh.fait_mesure_journaliere(id_secteur);
CREATE INDEX idx_fait_jour_point   ON dwh.fait_mesure_journaliere(id_point_mesure);
CREATE INDEX idx_fait_jour_source  ON dwh.fait_mesure_journaliere(id_source_mesure);
CREATE INDEX idx_fait_jour_voie    ON dwh.fait_mesure_journaliere(voie);

COMMENT ON TABLE dwh.fait_mesure_journaliere IS 
    'Agrégats journaliers calculés depuis les mesures temps réel';
COMMENT ON COLUMN dwh.fait_mesure_journaliere.pct_min_sur_moy IS 
    'Ratio débit min / débit moyen. Un ratio < 30% peut indiquer une bonne isolation nuit';


-- ─────────────────────────────────────────────────────────────
-- FAIT_BILAN_PERIODE
-- Granularité : 1 ligne = 1 point × 1 période (mois principalement)
-- Correspond à "Fact_Reservoir_Mois" du dashboard PBI existant
-- ─────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dwh.fait_bilan_periode CASCADE;
CREATE TABLE dwh.fait_bilan_periode (
    id_fait                 BIGSERIAL PRIMARY KEY,
    
    -- ─── Clés de dimension (conforme schéma : Etage inclus, pas Secteur) ───
    id_temps_debut          INTEGER NOT NULL 
                            REFERENCES dwh.dim_temps(id_temps),
    id_temps_fin            INTEGER NOT NULL 
                            REFERENCES dwh.dim_temps(id_temps),
    id_point_mesure         INTEGER NOT NULL 
                            REFERENCES dwh.dim_point_mesure(id_point_mesure),
    id_etage                INTEGER NOT NULL DEFAULT 0
                            REFERENCES dwh.dim_etage(id_etage),
    id_source_mesure        INTEGER NOT NULL 
                            REFERENCES dwh.dim_source_mesure(id_source_mesure),
    
    -- ─── Mesures du schéma constellation ───
    index_jour_debut        DOUBLE PRECISION,             -- Index premier jour
    index_jour_fin          DOUBLE PRECISION,             -- Index dernier jour
    volume_periode          DOUBLE PRECISION,             -- Différence (fin - debut)
    nb_jours_periode        INTEGER,                      -- Nombre de jours calendaires
    
    -- ─── Métadonnées techniques ───
    type_periode            VARCHAR(20) DEFAULT 'MOIS',   -- MOIS|SEMAINE|CUSTOM
    voie                    VARCHAR(20) DEFAULT 'INDEX',  -- Généralement INDEX
    est_calcul_valide       BOOLEAN DEFAULT TRUE,         -- FALSE si vol_periode < 0
    qualite_donnees         VARCHAR(20) DEFAULT 'GOOD',
    date_calcul             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_fait_bilan UNIQUE (id_point_mesure, id_temps_debut, id_temps_fin, voie)
);

CREATE INDEX idx_fait_bilan_debut ON dwh.fait_bilan_periode(id_temps_debut);
CREATE INDEX idx_fait_bilan_fin   ON dwh.fait_bilan_periode(id_temps_fin);
CREATE INDEX idx_fait_bilan_point ON dwh.fait_bilan_periode(id_point_mesure);
CREATE INDEX idx_fait_bilan_etage ON dwh.fait_bilan_periode(id_etage);
CREATE INDEX idx_fait_bilan_type  ON dwh.fait_bilan_periode(type_periode);

COMMENT ON TABLE dwh.fait_bilan_periode IS 
    'Bilans de consommation sur une période (correspond à Fact_Reservoir_Mois du PBI)';
COMMENT ON COLUMN dwh.fait_bilan_periode.est_calcul_valide IS 
    'FALSE quand volume_periode < 0 (probable remise à zéro du compteur)';