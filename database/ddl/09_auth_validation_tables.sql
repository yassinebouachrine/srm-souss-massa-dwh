-- database/ddl/09_auth_validation_tables.sql

-- ════════════════════════════════════════════════════════════════
-- SCHEMA pour l'application Streamlit
-- ════════════════════════════════════════════════════════════════
CREATE SCHEMA IF NOT EXISTS app_auth;
CREATE SCHEMA IF NOT EXISTS app_staging;

-- ════════════════════════════════════════════════════════════════
-- TABLE: Utilisateurs
-- ════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS app_auth.utilisateurs (
    id_utilisateur      SERIAL PRIMARY KEY,
    username            VARCHAR(100) UNIQUE NOT NULL,
    password_hash       VARCHAR(255) NOT NULL,
    nom_complet         VARCHAR(200) NOT NULL,
    email               VARCHAR(200),
    role                VARCHAR(50) NOT NULL CHECK (role IN (
                            'agent_dp', 
                            'admin_dp', 
                            'admin_regional', 
                            'super_admin'
                        )),
    id_province         INTEGER REFERENCES gold.dim_province(id_province),
    code_province       VARCHAR(50),
    est_actif           BOOLEAN DEFAULT TRUE,
    derniere_connexion  TIMESTAMP,
    tentatives_echouees INTEGER DEFAULT 0,
    verrouille_jusqua   TIMESTAMP,
    date_creation       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modification   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ════════════════════════════════════════════════════════════════
-- TABLE: Sessions
-- ════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS app_auth.sessions (
    id_session          SERIAL PRIMARY KEY,
    id_utilisateur      INTEGER REFERENCES app_auth.utilisateurs(id_utilisateur),
    token_session       VARCHAR(255) UNIQUE NOT NULL,
    ip_address          VARCHAR(50),
    user_agent          TEXT,
    date_creation       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_expiration     TIMESTAMP NOT NULL,
    est_active          BOOLEAN DEFAULT TRUE
);

-- ════════════════════════════════════════════════════════════════
-- TABLE: Logs d'audit
-- ════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS app_auth.audit_logs (
    id_log              SERIAL PRIMARY KEY,
    id_utilisateur      INTEGER REFERENCES app_auth.utilisateurs(id_utilisateur),
    action              VARCHAR(100) NOT NULL,
    table_cible         VARCHAR(100),
    id_enregistrement   INTEGER,
    details             JSONB,
    ip_address          VARCHAR(50),
    date_action         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ════════════════════════════════════════════════════════════════
-- TABLE: Staging Indicateurs DP (données en attente de validation)
-- ════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS app_staging.staging_indicateurs_dp (
    id_staging          SERIAL PRIMARY KEY,
    
    -- Données métier
    id_province         INTEGER NOT NULL,
    nom_province        VARCHAR(100),
    id_centre           INTEGER,
    nom_centre          VARCHAR(200),
    annee               INTEGER NOT NULL,
    mois                INTEGER NOT NULL,
    nom_mois            VARCHAR(20),
    code_indicateur     VARCHAR(50) NOT NULL,
    libelle_indicateur  VARCHAR(200),
    unite               VARCHAR(50),
    categorie           VARCHAR(100),
    valeur_mensuelle    FLOAT,
    valeur_recapitulatif FLOAT,
    
    -- Métadonnées de workflow
    statut              VARCHAR(50) DEFAULT 'brouillon' CHECK (statut IN (
                            'brouillon', 'soumis', 'valide_dp', 'rejete_dp',
                            'valide_regional', 'rejete_regional'
                        )),
    soumis_par          INTEGER REFERENCES app_auth.utilisateurs(id_utilisateur),
    date_soumission     TIMESTAMP,
    
    valide_par_dp       INTEGER REFERENCES app_auth.utilisateurs(id_utilisateur),
    date_validation_dp  TIMESTAMP,
    commentaire_dp      TEXT,
    
    valide_par_regional INTEGER REFERENCES app_auth.utilisateurs(id_utilisateur),
    date_validation_reg TIMESTAMP,
    commentaire_regional TEXT,
    
    date_creation       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modification   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Lot de saisie
    lot_id              VARCHAR(100),
    
    CONSTRAINT uq_staging_indic UNIQUE (id_province, id_centre, annee, mois, code_indicateur, lot_id)
);

-- ════════════════════════════════════════════════════════════════
-- TABLE: Staging Réclamations DP (données en attente de validation)
-- ════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS app_staging.staging_reclamations_dp (
    id_staging          SERIAL PRIMARY KEY,
    
    -- Données métier
    id_province         INTEGER NOT NULL,
    nom_province        VARCHAR(100),
    id_centre           INTEGER,
    nom_centre          VARCHAR(200),
    annee               INTEGER NOT NULL,
    mois                INTEGER NOT NULL,
    code_type           VARCHAR(50) NOT NULL,
    libelle_reclamation VARCHAR(200),
    categorie_reclamation VARCHAR(100),
    nombre_reclamations INTEGER DEFAULT 0,
    temps_moyen_coupure_h FLOAT DEFAULT 0,
    delai_moyen_traitement_j FLOAT DEFAULT 0,
    valeur_brute        FLOAT DEFAULT 0,
    
    -- Métadonnées de workflow
    statut              VARCHAR(50) DEFAULT 'brouillon' CHECK (statut IN (
                            'brouillon', 'soumis', 'valide_dp', 'rejete_dp',
                            'valide_regional', 'rejete_regional'
                        )),
    soumis_par          INTEGER REFERENCES app_auth.utilisateurs(id_utilisateur),
    date_soumission     TIMESTAMP,
    
    valide_par_dp       INTEGER REFERENCES app_auth.utilisateurs(id_utilisateur),
    date_validation_dp  TIMESTAMP,
    commentaire_dp      TEXT,
    
    valide_par_regional INTEGER REFERENCES app_auth.utilisateurs(id_utilisateur),
    date_validation_reg TIMESTAMP,
    commentaire_regional TEXT,
    
    date_creation       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modification   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    lot_id              VARCHAR(100),
    
    CONSTRAINT uq_staging_reclam UNIQUE (id_province, id_centre, annee, mois, code_type, lot_id)
);

-- ════════════════════════════════════════════════════════════════
-- INDEX
-- ════════════════════════════════════════════════════════════════
CREATE INDEX IF NOT EXISTS idx_staging_indic_statut ON app_staging.staging_indicateurs_dp(statut);
CREATE INDEX IF NOT EXISTS idx_staging_indic_province ON app_staging.staging_indicateurs_dp(id_province);
CREATE INDEX IF NOT EXISTS idx_staging_indic_lot ON app_staging.staging_indicateurs_dp(lot_id);
CREATE INDEX IF NOT EXISTS idx_staging_reclam_statut ON app_staging.staging_reclamations_dp(statut);
CREATE INDEX IF NOT EXISTS idx_staging_reclam_province ON app_staging.staging_reclamations_dp(id_province);
CREATE INDEX IF NOT EXISTS idx_staging_reclam_lot ON app_staging.staging_reclamations_dp(lot_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON app_auth.audit_logs(id_utilisateur);
CREATE INDEX IF NOT EXISTS idx_audit_logs_date ON app_auth.audit_logs(date_action);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON app_auth.sessions(token_session);
CREATE INDEX IF NOT EXISTS idx_utilisateurs_username ON app_auth.utilisateurs(username);