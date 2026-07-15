-- ═══════════════════════════════════════════════════════════════
-- SEED — 6 provinces de Souss-Massa
-- ═══════════════════════════════════════════════════════════════

INSERT INTO app_staging.ref_province (id_province, code_province, nom_province, est_siege) VALUES
(1, 'TATA',        'Tata',                 FALSE),
(2, 'TIZNIT',      'Tiznit',               FALSE),
(3, 'CHTOUKA',     'Chtouka Ait Baha',     FALSE),
(4, 'TAROUDANT',   'Taroudant',            FALSE),
(5, 'INEZGANE',    'Inezgane Ait Melloul', FALSE),
(6, 'AGADIR',      'Agadir',               TRUE)  -- Siège
ON CONFLICT (id_province) DO UPDATE
SET nom_province = EXCLUDED.nom_province,
    est_siege = EXCLUDED.est_siege;