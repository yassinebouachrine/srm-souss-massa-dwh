-- ============================================================
-- Fichier : 00_create_schemas.sql
-- Projet  : SRM Souss-Massa DWH
-- Date    : Juillet 2026
-- ============================================================

-- TODO: Ajouter les instructions SQL ici
-- ============================================================
-- Fichier : 00_create_schemas.sql
-- Projet  : SRM Souss-Massa DWH
-- Objectif: Creer les 5 schemas de l'architecture medaillon
-- ============================================================

-- Schema STAGING : Donnees saisies via Streamlit
CREATE SCHEMA IF NOT EXISTS staging;
COMMENT ON SCHEMA staging IS 
    'Zone de saisie temporaire alimentee par Streamlit';

-- Schema BRONZE : Donnees brutes horodatees
CREATE SCHEMA IF NOT EXISTS bronze;
COMMENT ON SCHEMA bronze IS 
    'Donnees brutes ingerees depuis toutes les sources';

-- Schema SILVER : Donnees nettoyees
CREATE SCHEMA IF NOT EXISTS silver;
COMMENT ON SCHEMA silver IS 
    'Donnees nettoyees, validees et enrichies';

-- Schema GOLD : Data Warehouse (constellation)
CREATE SCHEMA IF NOT EXISTS gold;
COMMENT ON SCHEMA gold IS 
    'Data Warehouse - Schema en constellation';

-- Schema AUDIT : Tracabilite et logs
CREATE SCHEMA IF NOT EXISTS audit;
COMMENT ON SCHEMA audit IS 
    'Logs et tracabilite des operations';

-- ============================================================
-- Verification
-- ============================================================
SELECT 
    schema_name,
    obj_description(oid, 'pg_namespace') AS description
FROM information_schema.schemata s
JOIN pg_namespace n ON n.nspname = s.schema_name
WHERE schema_name IN ('staging', 'bronze', 'silver', 'gold', 'audit')
ORDER BY schema_name;