-- ═══════════════════════════════════════════════════════════════
-- SEED DWH — Peuplement DIM_DP
-- (Aligné sur les 6 provinces de app_staging.ref_province)
-- ═══════════════════════════════════════════════════════════════

TRUNCATE TABLE dwh.dim_dp RESTART IDENTITY CASCADE;

INSERT INTO dwh.dim_dp (code_dp, nom_dp, region) VALUES
('DP_TATA',    'Tata',                    'Souss-Massa'),
('DP_TIZ',     'Tiznit',                  'Souss-Massa'),
('DP_CHT',     'Chtouka Ait Baha',        'Souss-Massa'),
('DP_TAR',     'Taroudant',               'Souss-Massa'),
('DP_INZ',     'Inezgane Ait Melloul',    'Souss-Massa'),
('DP_AGA',     'Agadir',                  'Souss-Massa');