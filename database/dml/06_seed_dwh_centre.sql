-- ═══════════════════════════════════════════════════════════════
-- SEED DWH — Peuplement DIM_CENTRE
-- Synchronisé avec app_staging.ref_centre
-- ═══════════════════════════════════════════════════════════════

TRUNCATE TABLE dwh.dim_centre RESTART IDENTITY CASCADE;

INSERT INTO dwh.dim_centre (code_centre, nom_centre, type_centre, code_dp, nom_dp)
SELECT 
    rc.code_centre,
    rc.nom_centre,
    rc.type_centre,
    CASE rp.code_province
        WHEN 'PROV_TATA' THEN 'DP_TATA'
        WHEN 'PROV_TIZ'  THEN 'DP_TIZ'
        WHEN 'PROV_CHT'  THEN 'DP_CHT'
        WHEN 'PROV_TAR'  THEN 'DP_TAR'
        WHEN 'PROV_INZ'  THEN 'DP_INZ'
        WHEN 'PROV_AGA'  THEN 'DP_AGA'
    END AS code_dp,
    rp.nom_province AS nom_dp
FROM app_staging.ref_centre rc
JOIN app_staging.ref_province rp ON rc.id_province = rp.id_province;