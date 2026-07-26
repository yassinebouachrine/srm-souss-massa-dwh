-- ═══════════════════════════════════════════════════════════════
-- SEED DWH — DIM_TYPE_INDICATEUR_DP
-- Synchronisé avec app_staging.ref_type_indicateur
-- ═══════════════════════════════════════════════════════════════

TRUNCATE TABLE dwh.dim_type_indicateur_dp RESTART IDENTITY CASCADE;

INSERT INTO dwh.dim_type_indicateur_dp (code_indicateur, libelle_indicateur, unite, categorie)
SELECT code_indicateur, libelle_indicateur, unite, categorie
FROM app_staging.ref_type_indicateur
WHERE est_actif = TRUE
ORDER BY ordre_affichage;