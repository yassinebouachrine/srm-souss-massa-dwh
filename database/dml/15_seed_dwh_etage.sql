-- ═══════════════════════════════════════════════════════════════
-- SEED — DIM_ETAGE
-- Étages hydrauliques identifiés depuis "Linéaire Par étage.xlsx"
-- 
-- Le nombre à la fin du nom = cote d'altitude en mètres du réservoir
-- Ex: "TASSILA 75" → réservoir à 75m d'altitude
-- ═══════════════════════════════════════════════════════════════

-- IMPORTANT : ne PAS truncate (sinon on perd la sentinelle id=0 créée dans le DDL)
-- On utilise INSERT ... ON CONFLICT pour être idempotent

-- Réactiver la sentinelle si perdue
INSERT INTO dwh.dim_etage 
    (id_etage, code_etage, nom_etage, type_etage, nom_region, est_actif)
VALUES 
    (0, 'ETAGE_INCONNU', 'Étage Non Renseigné', 'Inconnu', 'Souss-Massa', TRUE)
ON CONFLICT (id_etage) DO NOTHING;


-- ─── Étages principaux (ID 1-20) ───
INSERT INTO dwh.dim_etage 
    (id_etage, code_etage, nom_etage, type_etage, lineaire_km, cote_altitude, nom_region, nom_province)
VALUES
    -- TASSILA (le plus grand système)
    (1,  'ETAGE_TASSILA_75',   'TASSILA 75',            'Réservoir', 1050.531, 75,  'Souss-Massa', 'Agadir'),
    (2,  'ETAGE_TASSILA_104',  'TASSILA 104',           'Réservoir', 392.881,  104, 'Souss-Massa', 'Agadir'),
    
    -- BOUARGANE
    (3,  'ETAGE_BOUARGANE_85', 'BOUARGANE 85',          'Réservoir', 128.448,  85,  'Souss-Massa', 'Agadir'),
    (4,  'ETAGE_BOUARGANE_130','BOUARGANE 130',         'Réservoir', 333.379,  130, 'Souss-Massa', 'Agadir'),
    
    -- MASSIRA
    (5,  'ETAGE_MASSIRA_75',   'MASSIRA 75',            'Réservoir', 139.757,  75,  'Souss-Massa', 'Agadir'),
    
    -- HAY MOHAMMADI & ILLIGH
    (6,  'ETAGE_HAY_MOHAM_210','HAY MOHAMMADI 210',     'Réservoir', 71.660,   210, 'Souss-Massa', 'Agadir'),
    (7,  'ETAGE_ILLIGH_175',   'ILLIGH 175',            'Réservoir', 79.602,   175, 'Souss-Massa', 'Agadir'),
    
    -- TADDART
    (8,  'ETAGE_TADDART_245',  'TADDART 245',           'Réservoir', 105.202,  245, 'Souss-Massa', 'Agadir'),
    
    -- ANZA
    (9,  'ETAGE_ANZA_70',      'ANZA 70',               'Réservoir', 51.952,   70,  'Souss-Massa', 'Agadir'),
    (10, 'ETAGE_ANZA_101',     'ANZA 101',              'Réservoir', NULL,     101, 'Souss-Massa', 'Agadir'),
    
    -- TAGADIRT
    (11, 'ETAGE_TAGADIRT_129', 'TAGADIRT 129',          'Réservoir', 97.527,   129, 'Souss-Massa', 'Agadir'),
    
    -- AOURIR / TAMRAGHT
    (12, 'ETAGE_TAMRAGHT_125', 'TAMRAGHT 125',          'Réservoir', 51.869,   125, 'Souss-Massa', 'Agadir'),
    (13, 'ETAGE_AOURIR_130',   'AOURIR TAMA OUANZA COTE 130', 'Réservoir', 82.056, 130, 'Souss-Massa', 'Agadir'),
    (14, 'ETAGE_AOURIR_TAM',   'Aourir + Tamraght (Loc80)',   'Agrégation', NULL, NULL, 'Souss-Massa', 'Agadir'),
    
    -- Autres étages
    (15, 'ETAGE_AIT_MOUDEN',   'AIT EL MOUDEN',         'Réservoir', 26.929,   NULL, 'Souss-Massa', 'Agadir'),
    (16, 'ETAGE_IGHIL_OUD',    'IGHIL OUDERDOUR',       'Réservoir', 7.691,    NULL, 'Souss-Massa', 'Agadir')

ON CONFLICT (id_etage) DO UPDATE
SET code_etage    = EXCLUDED.code_etage,
    nom_etage     = EXCLUDED.nom_etage,
    type_etage    = EXCLUDED.type_etage,
    lineaire_km   = EXCLUDED.lineaire_km,
    cote_altitude = EXCLUDED.cote_altitude,
    nom_province  = EXCLUDED.nom_province;


-- ─── Étages "roll-up" agrégés (ID 90+) ───
-- Utilisés pour les rapports consolidés (bilans hydrauliques)
INSERT INTO dwh.dim_etage 
    (id_etage, code_etage, nom_etage, type_etage, nom_region, nom_province)
VALUES
    (90, 'ETAGE_B130_T104',   'B130+ T104',           'Agrégation', 'Souss-Massa', 'Agadir'),
    (91, 'ETAGE_B85_M75',     'B 85+ M75',            'Agrégation', 'Souss-Massa', 'Agadir'),
    (92, 'ETAGE_HAYM_ILLIGH', 'Hay M + ILLIGH 175',   'Agrégation', 'Souss-Massa', 'Agadir'),
    (93, 'ETAGE_AOUR_TAMR',   'AOURIR + TAMRAGHT',    'Agrégation', 'Souss-Massa', 'Agadir')

ON CONFLICT (id_etage) DO UPDATE
SET code_etage = EXCLUDED.code_etage,
    nom_etage  = EXCLUDED.nom_etage,
    type_etage = EXCLUDED.type_etage;


-- Vérification
SELECT id_etage, code_etage, nom_etage, type_etage, lineaire_km, cote_altitude 
FROM dwh.dim_etage 
ORDER BY id_etage;