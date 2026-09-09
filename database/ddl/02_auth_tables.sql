-- ═══════════════════════════════════════════════════════════════
-- SCHÉMA APP_AUTH — Sécurité et Utilisateurs (Normalisé 3NF)
-- ═══════════════════════════════════════════════════════════════

-- ─── 1. Table Utilisateurs ───
DROP TABLE IF EXISTS app_auth.utilisateurs CASCADE;
CREATE TABLE app_auth.utilisateurs (
    id_utilisateur          SERIAL PRIMARY KEY,
    username                VARCHAR(100) UNIQUE NOT NULL,
    password_hash           VARCHAR(255) NOT NULL,
    nom_complet             VARCHAR(200) NOT NULL,
    email                   VARCHAR(200),
    id_role                 INTEGER NOT NULL REFERENCES app_auth.ref_role(id_role),
    id_province             INTEGER REFERENCES app_staging.ref_province(id_province),
    est_actif               BOOLEAN DEFAULT TRUE,
    derniere_connexion      TIMESTAMP,
    tentatives_echouees     INTEGER DEFAULT 0,
    verrouille_jusqua       TIMESTAMP,
    date_creation           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modification       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── 2. Table Sessions (Sécurisée + Restauration F5 via sid_public) ───
DROP TABLE IF EXISTS app_auth.sessions CASCADE;
CREATE TABLE app_auth.sessions (
    id_session              BIGSERIAL PRIMARY KEY,
    id_utilisateur          INTEGER NOT NULL REFERENCES app_auth.utilisateurs(id_utilisateur) ON DELETE CASCADE,
    token_hash              VARCHAR(255) UNIQUE NOT NULL,
    sid_public              VARCHAR(16) UNIQUE NOT NULL,
    date_expiration         TIMESTAMP NOT NULL,
    est_active              BOOLEAN DEFAULT TRUE,
    date_creation           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── 3. Table Réinitialisation Mot de passe ───
DROP TABLE IF EXISTS app_auth.password_reset_tokens CASCADE;
CREATE TABLE app_auth.password_reset_tokens (
    id_reset                BIGSERIAL PRIMARY KEY,
    id_utilisateur          INTEGER NOT NULL REFERENCES app_auth.utilisateurs(id_utilisateur) ON DELETE CASCADE,
    token_hash              VARCHAR(255) UNIQUE NOT NULL,
    date_expiration         TIMESTAMP NOT NULL,
    utilise                 BOOLEAN DEFAULT FALSE,
    date_creation           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── 4. Table Logs d'Audit ───
DROP TABLE IF EXISTS app_auth.audit_logs CASCADE;
CREATE TABLE app_auth.audit_logs (
    id_log                  BIGSERIAL PRIMARY KEY,
    id_utilisateur          INTEGER REFERENCES app_auth.utilisateurs(id_utilisateur) ON DELETE SET NULL,
    action                  VARCHAR(100) NOT NULL,
    table_cible             VARCHAR(100),
    id_enregistrement       BIGINT,
    details                 JSONB,
    date_action             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── Index de performance (avec IF NOT EXISTS) ───
CREATE INDEX IF NOT EXISTS idx_utilisateurs_role ON app_auth.utilisateurs(id_role);
CREATE INDEX IF NOT EXISTS idx_utilisateurs_prov ON app_auth.utilisateurs(id_province);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON app_auth.sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_sid ON app_auth.sessions(sid_public);
CREATE INDEX IF NOT EXISTS idx_audit_user ON app_auth.audit_logs(id_utilisateur);
CREATE INDEX IF NOT EXISTS idx_audit_date ON app_auth.audit_logs(date_action);