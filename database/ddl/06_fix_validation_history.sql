-- ═══════════════════════════════════════════════════════════════
-- FIX : Permettre plusieurs validations par (donnée, niveau)
-- pour garder l'historique complet des rejets/corrections successifs
-- ═══════════════════════════════════════════════════════════════

-- Supprimer la contrainte UNIQUE qui empêche l'historique
ALTER TABLE app_staging.validation 
    DROP CONSTRAINT IF EXISTS uq_validation_donnee_niveau;

-- Ajouter un index simple pour les performances
CREATE INDEX IF NOT EXISTS idx_validation_donnee_niveau_date 
    ON app_staging.validation(id_donnee, niveau, date_validation DESC);

COMMENT ON TABLE app_staging.validation IS
    'Historique COMPLET des décisions : plusieurs lignes par (donnée, niveau) autorisées pour tracer chaque rejet successif.';