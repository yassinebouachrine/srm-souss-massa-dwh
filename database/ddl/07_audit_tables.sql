-- ============================================================
-- Fichier : 07_audit_tables.sql
-- Objectif: 3 tables audit et tracabilite
-- ============================================================

SET search_path TO audit;

-- ────────────────────────────────────────────
-- 1. AUDIT : Log des saisies utilisateurs
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS audit.log_saisies CASCADE;

CREATE TABLE audit.log_saisies (
    id_log              BIGSERIAL PRIMARY KEY,
    utilisateur         VARCHAR(100),
    action              VARCHAR(20) 
                        CHECK (action IN ('INSERT', 'UPDATE', 'DELETE', 'VALIDATE', 'REJECT')),
    table_cible         VARCHAR(100),
    id_enregistrement   BIGINT,
    donnees_avant       JSONB,
    donnees_apres       JSONB,
    ip_client           VARCHAR(50),
    user_agent          TEXT,
    date_action         TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE audit.log_saisies IS 
    'Log complet des saisies utilisateurs via Streamlit';


-- ────────────────────────────────────────────
-- 2. AUDIT : Log des modifications
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS audit.log_modifications CASCADE;

CREATE TABLE audit.log_modifications (
    id_log              BIGSERIAL PRIMARY KEY,
    table_source        VARCHAR(100),
    id_ligne_source     BIGINT,
    champ_modifie       VARCHAR(100),
    ancienne_valeur     TEXT,
    nouvelle_valeur     TEXT,
    modifie_par         VARCHAR(100),
    raison_modification TEXT,
    date_modification   TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE audit.log_modifications IS 
    'Historique detaille des modifications de donnees';


-- ────────────────────────────────────────────
-- 3. AUDIT : Log des executions ETL
-- ────────────────────────────────────────────
DROP TABLE IF EXISTS audit.log_etl CASCADE;

CREATE TABLE audit.log_etl (
    id_log              BIGSERIAL PRIMARY KEY,
    dag_id              VARCHAR(100),
    task_id             VARCHAR(100),
    execution_date      TIMESTAMP,
    duree_secondes      INTEGER,
    statut              VARCHAR(20) 
                        CHECK (statut IN ('SUCCESS', 'FAILED', 'RUNNING', 'SKIPPED')),
    nb_lignes_lues      INTEGER DEFAULT 0,
    nb_lignes_ecrites   INTEGER DEFAULT 0,
    nb_lignes_rejetees  INTEGER DEFAULT 0,
    message_erreur      TEXT,
    metadata            JSONB,
    date_creation       TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE audit.log_etl IS 
    'Log des executions des DAGs Airflow';


-- ────────────────────────────────────────────
-- Verification
-- ────────────────────────────────────────────
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns 
     WHERE table_schema = 'audit' AND table_name = t.table_name) AS nb_colonnes
FROM information_schema.tables t
WHERE table_schema = 'audit'
ORDER BY table_name;