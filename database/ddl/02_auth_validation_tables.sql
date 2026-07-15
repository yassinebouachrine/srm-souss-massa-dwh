-- ═══════════════════════════════════════════════════════════════
-- SCHÉMA APP_AUTH — Tables d'authentification Streamlit
-- ═══════════════════════════════════════════════════════════════

-- ─── Table utilisateurs ───
CREATE TABLE IF NOT EXISTS app_auth.utilisateurs (
    id_utilisateur          SERIAL PRIMARY KEY,
    username                VARCHAR(100) UNIQUE NOT NULL,
    password_hash           VARCHAR(255) NOT NULL,
    nom_complet             VARCHAR(200) NOT NULL,
    email                   VARCHAR(200),
    role                    VARCHAR(50) NOT NULL,
    id_province             INTEGER REFERENCES app_staging.ref_province(id_province),  -- 🔧 Corrigé
    code_province           VARCHAR(20),
    est_actif               BOOLEAN DEFAULT TRUE,
    derniere_connexion      TIMESTAMP,
    tentatives_echouees     INTEGER DEFAULT 0,
    verrouille_jusqua       TIMESTAMP,
    date_creation           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modification       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── Table sessions ───
CREATE TABLE IF NOT EXISTS app_auth.sessions (
    id_session              SERIAL PRIMARY KEY,
    id_utilisateur          INTEGER REFERENCES app_auth.utilisateurs(id_utilisateur),
    token_session           VARCHAR(255) UNIQUE NOT NULL,
    date_expiration         TIMESTAMP NOT NULL,
    est_active              BOOLEAN DEFAULT TRUE,
    date_creation           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── Table logs d'audit ───
CREATE TABLE IF NOT EXISTS app_auth.audit_logs (
    id_log                  BIGSERIAL PRIMARY KEY,
    id_utilisateur          INTEGER REFERENCES app_auth.utilisateurs(id_utilisateur),
    action                  VARCHAR(100) NOT NULL,
    table_cible             VARCHAR(100),
    id_enregistrement       INTEGER,
    details                 JSONB,
    date_action             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ═══════════════════════════════════════════════════════════════
-- SCHÉMA APP_STAGING — Données saisies Streamlit
-- ═══════════════════════════════════════════════════════════════

-- ─── Staging Indicateurs DP ───
CREATE TABLE IF NOT EXISTS app_staging.staging_indicateurs_dp (
    id_staging              BIGSERIAL PRIMARY KEY,
    id_province             INTEGER NOT NULL REFERENCES app_staging.ref_province(id_province),
    nom_province            VARCHAR(100),
    id_centre               INTEGER REFERENCES app_staging.ref_centre(id_centre),
    nom_centre              VARCHAR(200),
    annee                   INTEGER NOT NULL,
    mois                    INTEGER NOT NULL,
    nom_mois                VARCHAR(20),
    code_indicateur         VARCHAR(50) NOT NULL,
    libelle_indicateur      VARCHAR(200),
    unite                   VARCHAR(50),
    categorie               VARCHAR(100),
    valeur_indicateur       DOUBLE PRECISION,
    statut                  VARCHAR(50) DEFAULT 'brouillon',
    soumis_par              INTEGER REFERENCES app_auth.utilisateurs(id_utilisateur),
    date_soumission         TIMESTAMP,
    valide_par_dp           INTEGER REFERENCES app_auth.utilisateurs(id_utilisateur),
    date_validation_dp      TIMESTAMP,
    commentaire_dp          TEXT,
    valide_par_regional     INTEGER REFERENCES app_auth.utilisateurs(id_utilisateur),
    date_validation_reg     TIMESTAMP,
    commentaire_regional    TEXT,
    lot_id                  VARCHAR(100),
    date_creation           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modification       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_stg_indic UNIQUE (id_province, id_centre, annee, mois, code_indicateur, lot_id)
);

-- ─── Staging Réclamations DP ───
CREATE TABLE IF NOT EXISTS app_staging.staging_reclamations_dp (
    id_staging              BIGSERIAL PRIMARY KEY,
    id_province             INTEGER NOT NULL REFERENCES app_staging.ref_province(id_province),
    nom_province            VARCHAR(100),
    id_centre               INTEGER REFERENCES app_staging.ref_centre(id_centre),
    nom_centre              VARCHAR(200),
    annee                   INTEGER NOT NULL,
    mois                    INTEGER NOT NULL,
    code_type               VARCHAR(50) NOT NULL,
    libelle_reclamation     VARCHAR(200),
    categorie_reclamation   VARCHAR(100),
    nombre_reclamations     INTEGER DEFAULT 0,
    temps_moyen_coupure_h   DOUBLE PRECISION DEFAULT 0,
    delai_moyen_traitement_j DOUBLE PRECISION DEFAULT 0,
    valeur_brute            DOUBLE PRECISION DEFAULT 0,
    statut                  VARCHAR(50) DEFAULT 'brouillon',
    soumis_par              INTEGER REFERENCES app_auth.utilisateurs(id_utilisateur),
    date_soumission         TIMESTAMP,
    valide_par_dp           INTEGER REFERENCES app_auth.utilisateurs(id_utilisateur),
    date_validation_dp      TIMESTAMP,
    commentaire_dp          TEXT,
    valide_par_regional     INTEGER REFERENCES app_auth.utilisateurs(id_utilisateur),
    date_validation_reg     TIMESTAMP,
    commentaire_regional    TEXT,
    lot_id                  VARCHAR(100),
    date_creation           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modification       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_stg_reclam UNIQUE (id_province, id_centre, annee, mois, code_type, lot_id)
);

-- ─── Index ───
CREATE INDEX IF NOT EXISTS idx_utilisateurs_username ON app_auth.utilisateurs(username);
CREATE INDEX IF NOT EXISTS idx_utilisateurs_role ON app_auth.utilisateurs(role);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON app_auth.sessions(token_session);
CREATE INDEX IF NOT EXISTS idx_audit_user ON app_auth.audit_logs(id_utilisateur);
CREATE INDEX IF NOT EXISTS idx_audit_date ON app_auth.audit_logs(date_action);

CREATE INDEX IF NOT EXISTS idx_stg_indic_statut ON app_staging.staging_indicateurs_dp(statut);
CREATE INDEX IF NOT EXISTS idx_stg_indic_province ON app_staging.staging_indicateurs_dp(id_province);
CREATE INDEX IF NOT EXISTS idx_stg_indic_lot ON app_staging.staging_indicateurs_dp(lot_id);

CREATE INDEX IF NOT EXISTS idx_stg_reclam_statut ON app_staging.staging_reclamations_dp(statut);
CREATE INDEX IF NOT EXISTS idx_stg_reclam_province ON app_staging.staging_reclamations_dp(id_province);
CREATE INDEX IF NOT EXISTS idx_stg_reclam_lot ON app_staging.staging_reclamations_dp(lot_id);