-- ═══════════════════════════════════════════════════════════════
-- VALIDATION + CORRECTIONS (Historique complet autorisé)
-- ═══════════════════════════════════════════════════════════════

-- ─── 1. Table VALIDATION ───
DROP TABLE IF EXISTS app_staging.validation CASCADE;
CREATE TABLE app_staging.validation (
    id_validation       BIGSERIAL PRIMARY KEY,
    id_donnee           BIGINT NOT NULL REFERENCES app_staging.donnee_saisie(id_donnee) ON DELETE CASCADE,
    niveau              VARCHAR(30) NOT NULL CHECK (niveau IN ('dp', 'regional')),
    decision            VARCHAR(30) NOT NULL CHECK (decision IN ('valide', 'rejete')),
    commentaire         TEXT,
    valide_par          INTEGER NOT NULL REFERENCES app_auth.utilisateurs(id_utilisateur),
    date_validation     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- Pas de contrainte UNIQUE : plusieurs validations autorisées par (donnée, niveau)
    -- pour garder l'historique complet des rejets/corrections successifs
);

-- ─── 2. Table CORRECTION (suite à un rejet) ───
DROP TABLE IF EXISTS app_staging.correction CASCADE;
CREATE TABLE app_staging.correction (
    id_correction       BIGSERIAL PRIMARY KEY,
    id_validation       BIGINT NOT NULL REFERENCES app_staging.validation(id_validation) ON DELETE CASCADE,
    id_utilisateur      INTEGER NOT NULL REFERENCES app_auth.utilisateurs(id_utilisateur),
    date_correction     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    commentaire         TEXT
);

-- ─── 3. Table DETAIL CORRECTION (champ par champ) ───
DROP TABLE IF EXISTS app_staging.detail_correction CASCADE;
CREATE TABLE app_staging.detail_correction (
    id_detail           BIGSERIAL PRIMARY KEY,
    id_correction       BIGINT NOT NULL REFERENCES app_staging.correction(id_correction) ON DELETE CASCADE,
    champ_modifie       VARCHAR(100) NOT NULL,
    ancienne_valeur     TEXT,
    nouvelle_valeur     TEXT
);

-- ─── Index de performance ───
CREATE INDEX IF NOT EXISTS idx_validation_donnee   ON app_staging.validation(id_donnee);
CREATE INDEX IF NOT EXISTS idx_validation_niveau   ON app_staging.validation(niveau);
CREATE INDEX IF NOT EXISTS idx_validation_decision ON app_staging.validation(decision);
CREATE INDEX IF NOT EXISTS idx_validation_user     ON app_staging.validation(valide_par);
CREATE INDEX IF NOT EXISTS idx_validation_date     ON app_staging.validation(date_validation);
CREATE INDEX IF NOT EXISTS idx_validation_donnee_niveau_date 
    ON app_staging.validation(id_donnee, niveau, date_validation DESC);
CREATE INDEX IF NOT EXISTS idx_correction_validation ON app_staging.correction(id_validation);
CREATE INDEX IF NOT EXISTS idx_correction_user       ON app_staging.correction(id_utilisateur);
CREATE INDEX IF NOT EXISTS idx_detail_correction     ON app_staging.detail_correction(id_correction);

-- ─── Commentaires ───
COMMENT ON TABLE app_staging.validation IS
    'Historique COMPLET des décisions : plusieurs lignes par (donnée, niveau) autorisées pour tracer chaque rejet successif.';

COMMENT ON COLUMN app_staging.validation.commentaire IS
    'En cas de rejet : motif obligatoire. En cas de validation : commentaire optionnel.';