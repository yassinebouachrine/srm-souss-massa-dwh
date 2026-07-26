-- ═══════════════════════════════════════════════════════════════
-- SEED DWH — DIM_TYPE_RECLAMATION
-- ═══════════════════════════════════════════════════════════════

TRUNCATE TABLE dwh.dim_type_reclamation RESTART IDENTITY CASCADE;

INSERT INTO dwh.dim_type_reclamation (code, libelle, categorie)
SELECT code_type, libelle_reclamation, categorie_reclamation
FROM app_staging.ref_type_reclamation
WHERE est_actif = TRUE
ORDER BY ordre_affichage;