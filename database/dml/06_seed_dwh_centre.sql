-- ═══════════════════════════════════════════════════════════════
-- SEED DWH — Peuplement DIM_CENTRE
-- Synchronisé avec app_staging.ref_centre + app_staging.ref_province
-- ═══════════════════════════════════════════════════════════════

TRUNCATE TABLE dwh.dim_centre RESTART IDENTITY CASCADE;

INSERT INTO dwh.dim_centre (code_centre, nom_centre, type_centre, code_dp, nom_dp)
SELECT 
    rc.code_centre,
    rc.nom_centre,
    rc.type_centre,
    CASE rp.code_province
        WHEN 'TATA'      THEN 'DP_TATA'
        WHEN 'TIZNIT'    THEN 'DP_TIZ'
        WHEN 'CHTOUKA'   THEN 'DP_CHT'
        WHEN 'TAROUDANT' THEN 'DP_TAR'
        WHEN 'INEZGANE'  THEN 'DP_INZ'
        WHEN 'AGADIR'    THEN 'DP_AGA'
    END AS code_dp,
    rp.nom_province AS nom_dp
FROM app_staging.ref_centre rc
JOIN app_staging.ref_province rp ON rc.id_province = rp.id_province
ORDER BY rc.id_centre;