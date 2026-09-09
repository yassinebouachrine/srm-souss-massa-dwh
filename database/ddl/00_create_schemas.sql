-- ═══════════════════════════════════════════════════════════════
-- SRM Souss-Massa — Création des schémas
-- ═══════════════════════════════════════════════════════════════

CREATE SCHEMA IF NOT EXISTS app_auth;
CREATE SCHEMA IF NOT EXISTS app_staging;

COMMENT ON SCHEMA app_auth IS 'Authentification, Sécurité et Utilisateurs';
COMMENT ON SCHEMA app_staging IS 'Référentiels et données métiers saisies';

GRANT USAGE ON SCHEMA app_auth TO PUBLIC;
GRANT USAGE ON SCHEMA app_staging TO PUBLIC;