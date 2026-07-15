-- ═══════════════════════════════════════════════════════════════
-- SRM Souss-Massa — Création des schémas
-- ═══════════════════════════════════════════════════════════════

CREATE SCHEMA IF NOT EXISTS app_auth;
CREATE SCHEMA IF NOT EXISTS app_staging;

COMMENT ON SCHEMA app_auth IS 'Authentification et gestion des utilisateurs Streamlit';
COMMENT ON SCHEMA app_staging IS 'Données saisies via Streamlit + tables de référence';

GRANT USAGE ON SCHEMA app_auth TO PUBLIC;
GRANT USAGE ON SCHEMA app_staging TO PUBLIC;