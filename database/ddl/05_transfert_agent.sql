-- ═══════════════════════════════════════════════════════════════
-- Table de transfert admin_dp → agent_dp
-- Utilisée quand un admin_dp reçoit un rejet régional et décide
-- de renvoyer le lot à l'agent pour correction
-- ═══════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS app_staging.transfert_agent CASCADE;
CREATE TABLE app_staging.transfert_agent (
    id_transfert       BIGSERIAL PRIMARY KEY,
    id_lot             BIGINT NOT NULL REFERENCES app_staging.lot_saisie(id_lot) ON DELETE CASCADE,
    id_admin_dp        INTEGER NOT NULL REFERENCES app_auth.utilisateurs(id_utilisateur),
    commentaire        TEXT,
    date_transfert     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    traite             BOOLEAN DEFAULT FALSE,
    date_traitement    TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transfert_lot ON app_staging.transfert_agent(id_lot);
CREATE INDEX IF NOT EXISTS idx_transfert_admin ON app_staging.transfert_agent(id_admin_dp);
CREATE INDEX IF NOT EXISTS idx_transfert_traite ON app_staging.transfert_agent(traite);

COMMENT ON TABLE app_staging.transfert_agent IS 
    'Trace les transferts effectués par admin_dp vers agent_dp après un rejet régional.';