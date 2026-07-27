-- ═══════════════════════════════════════════════════════════════
-- SEED DWH — DIM_TYPE_RECLAMATION
-- Les types standards (y compris AUTRES) sont marqués est_personnalisee = FALSE
-- Les réclamations Streamlit custom seront ajoutées dynamiquement par l'ETL
-- ═══════════════════════════════════════════════════════════════

TRUNCATE TABLE dwh.dim_type_reclamation RESTART IDENTITY CASCADE;

INSERT INTO dwh.dim_type_reclamation (code, libelle, categorie, est_personnalisee)
SELECT 
    code_type, 
    libelle_reclamation, 
    categorie_reclamation,
    FALSE
FROM app_staging.ref_type_reclamation
WHERE est_actif = TRUE
ORDER BY ordre_affichage;