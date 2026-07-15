-- ═══════════════════════════════════════════════════════════════
-- Table d'historique des corrections
-- Trace les modifications faites après un rejet
-- ═══════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS app_staging.historique_corrections CASCADE;
CREATE TABLE app_staging.historique_corrections (
    id_historique           BIGSERIAL PRIMARY KEY,
    lot_id                  VARCHAR(100) NOT NULL,
    data_type               VARCHAR(20) NOT NULL,  -- 'indicateurs' ou 'reclamations'
    id_staging              BIGINT NOT NULL,
    code_element            VARCHAR(50),           -- code_indicateur ou code_type
    libelle_element         VARCHAR(200),          -- libellé pour affichage
    champ_modifie           VARCHAR(50) NOT NULL,  -- nom de la colonne modifiée
    ancienne_valeur         TEXT,
    nouvelle_valeur         TEXT,
    motif_rejet             TEXT,                  -- motif du rejet initial
    corrige_par             INTEGER REFERENCES app_auth.utilisateurs(id_utilisateur),
    role_correcteur         VARCHAR(50),           -- agent_dp ou admin_dp
    date_correction         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour recherches rapides
CREATE INDEX IF NOT EXISTS idx_hist_corr_lot ON app_staging.historique_corrections(lot_id);
CREATE INDEX IF NOT EXISTS idx_hist_corr_date ON app_staging.historique_corrections(date_correction);
CREATE INDEX IF NOT EXISTS idx_hist_corr_user ON app_staging.historique_corrections(corrige_par);

COMMENT ON TABLE app_staging.historique_corrections IS 
    'Historique des corrections effectuées sur les lots rejetés (traçabilité ancienne/nouvelle valeur)';