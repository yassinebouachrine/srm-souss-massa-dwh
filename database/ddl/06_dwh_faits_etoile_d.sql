-- ═══════════════════════════════════════════════════════════════
-- DWH — FAITS ÉTOILE D : Performance DP & Réclamations
-- ═══════════════════════════════════════════════════════════════

-- ─── FAIT_INDICATEURS_PERFORMANCE_DP ───
DROP TABLE IF EXISTS dwh.fait_indicateurs_performance_dp CASCADE;
CREATE TABLE dwh.fait_indicateurs_performance_dp (
    id_fait             BIGSERIAL PRIMARY KEY,
    id_temps            INTEGER NOT NULL REFERENCES dwh.dim_temps(id_temps),
    id_dp               INTEGER NOT NULL REFERENCES dwh.dim_dp(id_dp),
    id_centre           INTEGER NOT NULL REFERENCES dwh.dim_centre(id_centre),  -- NOT NULL (utilise 0 pour agrégation DP)
    id_type_indicateur  INTEGER NOT NULL REFERENCES dwh.dim_type_indicateur_dp(id_type_indicateur),
    valeur              DOUBLE PRECISION,
    source_saisie       VARCHAR(20) NOT NULL DEFAULT 'excel_legacy',
    fichier_source      VARCHAR(255),
    onglet_source       VARCHAR(100),
    date_chargement     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Contrainte unique classique (sans expression → compatible ON CONFLICT)
    CONSTRAINT uq_fait_indic UNIQUE (id_temps, id_dp, id_centre, id_type_indicateur, source_saisie)
);

CREATE INDEX idx_fait_indic_temps  ON dwh.fait_indicateurs_performance_dp(id_temps);
CREATE INDEX idx_fait_indic_dp     ON dwh.fait_indicateurs_performance_dp(id_dp);
CREATE INDEX idx_fait_indic_centre ON dwh.fait_indicateurs_performance_dp(id_centre);
CREATE INDEX idx_fait_indic_type   ON dwh.fait_indicateurs_performance_dp(id_type_indicateur);

-- ─── FAIT_RECLAMATION ───
DROP TABLE IF EXISTS dwh.fait_reclamation CASCADE;
CREATE TABLE dwh.fait_reclamation (
    id_fait                 BIGSERIAL PRIMARY KEY,
    id_temps                INTEGER NOT NULL REFERENCES dwh.dim_temps(id_temps),
    id_dp                   INTEGER NOT NULL REFERENCES dwh.dim_dp(id_dp),
    id_centre               INTEGER NOT NULL REFERENCES dwh.dim_centre(id_centre),  -- NOT NULL (utilise 0)
    id_type                 INTEGER NOT NULL REFERENCES dwh.dim_type_reclamation(id_type),
    nb_reclamations         INTEGER,
    temps_moyen_coupure     DOUBLE PRECISION,
    delai_moyen_traitement  DOUBLE PRECISION,
    valeur_brute            DOUBLE PRECISION,
    source_saisie           VARCHAR(20) NOT NULL DEFAULT 'excel_legacy',
    fichier_source          VARCHAR(255),
    onglet_source           VARCHAR(100),
    date_chargement         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_fait_reclam UNIQUE (id_temps, id_dp, id_centre, id_type, source_saisie)
);

CREATE INDEX idx_fait_reclam_temps  ON dwh.fait_reclamation(id_temps);
CREATE INDEX idx_fait_reclam_dp     ON dwh.fait_reclamation(id_dp);
CREATE INDEX idx_fait_reclam_centre ON dwh.fait_reclamation(id_centre);
CREATE INDEX idx_fait_reclam_type   ON dwh.fait_reclamation(id_type);

COMMENT ON COLUMN dwh.fait_indicateurs_performance_dp.source_saisie IS 
    'Origine : excel_legacy (ancien système) ou streamlit (nouvelle app)';
COMMENT ON COLUMN dwh.fait_indicateurs_performance_dp.id_centre IS 
    'Réfère dwh.dim_centre. Utiliser id_centre=0 (AGREG_DP) pour les agrégations niveau DP';
COMMENT ON COLUMN dwh.fait_reclamation.source_saisie IS 
    'Origine : excel_legacy (ancien système) ou streamlit (nouvelle app)';
COMMENT ON COLUMN dwh.fait_reclamation.id_centre IS 
    'Réfère dwh.dim_centre. Utiliser id_centre=0 (AGREG_DP) pour les agrégations niveau DP';