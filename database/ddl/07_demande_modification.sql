-- ═══════════════════════════════════════════════════════════════
-- Table de demandes de modification post-validation régional
-- Workflow : admin_regional → admin_dp → (optionnel) agent_dp
-- ═══════════════════════════════════════════════════════════════

-- 1. Étendre les statuts autorisés dans donnee_saisie
ALTER TABLE app_staging.donnee_saisie 
    DROP CONSTRAINT IF EXISTS donnee_saisie_statut_check;

ALTER TABLE app_staging.donnee_saisie 
    ADD CONSTRAINT donnee_saisie_statut_check 
    CHECK (statut IN (
        'brouillon', 'soumis', 
        'valide_dp', 'rejete_dp', 
        'valide_regional', 'rejete_regional',
        'modif_admin_dp',   -- ✅ NOUVEAU : chez admin_dp pour modification
        'modif_agent_dp'    -- ✅ NOUVEAU : chez agent pour modification
    ));

-- 2. Table demande_modification
DROP TABLE IF EXISTS app_staging.demande_modification CASCADE;
CREATE TABLE app_staging.demande_modification (
    id_demande         BIGSERIAL PRIMARY KEY,
    id_lot             BIGINT NOT NULL REFERENCES app_staging.lot_saisie(id_lot) ON DELETE CASCADE,
    id_demandeur       INTEGER NOT NULL REFERENCES app_auth.utilisateurs(id_utilisateur),
    role_demandeur     VARCHAR(50) NOT NULL,
    id_destinataire    INTEGER NOT NULL REFERENCES app_auth.utilisateurs(id_utilisateur),
    role_destinataire  VARCHAR(50) NOT NULL,
    commentaire        TEXT NOT NULL,
    statut             VARCHAR(30) DEFAULT 'en_attente' 
                       CHECK (statut IN ('en_attente', 'traite', 'annule')),
    date_demande       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_traitement    TIMESTAMP
);

CREATE INDEX idx_dm_destinataire ON app_staging.demande_modification(id_destinataire, statut);
CREATE INDEX idx_dm_lot ON app_staging.demande_modification(id_lot);
CREATE INDEX idx_dm_statut ON app_staging.demande_modification(statut);

COMMENT ON TABLE app_staging.demande_modification IS
    'Demandes de modification sur données déjà validées régional. 
     Workflow: admin_regional → admin_dp → (optionnel) agent_dp.';