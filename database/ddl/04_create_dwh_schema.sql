-- ═══════════════════════════════════════════════════════════════
-- SRM Souss-Massa — Création du schéma DWH
-- ═══════════════════════════════════════════════════════════════

CREATE SCHEMA IF NOT EXISTS dwh;

COMMENT ON SCHEMA dwh IS 'Data Warehouse — Schéma en constellation (Faits + Dimensions)';

GRANT USAGE ON SCHEMA dwh TO PUBLIC;