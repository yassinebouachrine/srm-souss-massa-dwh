-- ═══════════════════════════════════════════════════════════════
-- SEED — DIM_SECTEUR
-- Secteurs hydrauliques identifiés depuis "Linéaire Par Secteur 2026.xlsx"
-- Le linéaire est en mètres
-- ═══════════════════════════════════════════════════════════════

-- Réactiver la sentinelle si perdue
INSERT INTO dwh.dim_secteur 
    (id_secteur, code_secteur, nom_secteur, nom_region, est_actif)
VALUES 
    (0, 'SECTEUR_INCONNU', 'Secteur Non Renseigné', 'Souss-Massa', TRUE)
ON CONFLICT (id_secteur) DO NOTHING;


-- ─── Secteurs (identifiés depuis référentiel PBI + PMAC) ───
INSERT INTO dwh.dim_secteur 
    (id_secteur, code_secteur, nom_secteur, nom_secteur_hydraulique, lineaire_m, nom_region, nom_province)
VALUES
    (1,  'SEC_18_NOV',        'Secteur 18 Novembre',      'Secteur 18 Novembre',            13620,  'Souss-Massa', 'Agadir'),
    (2,  'SEC_75_MASSIRA',    '75 MASSIRA ADRAR',         '75 MASSIRA ADRAR',               51507,  'Souss-Massa', 'Agadir'),
    (3,  'SEC_AGDAL',         'AGDAL',                    'AGDAL',                          28369,  'Souss-Massa', 'Inezgane Ait Melloul'),
    (4,  'SEC_AGHROUD',       'AGHROUD',                  'AGHROUD',                        399,    'Souss-Massa', 'Agadir'),
    (5,  'SEC_AIT_MOUDDEN',   'AIT EL MOUDDEN',           'AIT EL MOUDDEN AIT TAOUKT',      26929,  'Souss-Massa', 'Agadir'),
    (6,  'SEC_AM_PRISON',     'AIT MELOUL PRISON',        'AIT MELOUL PRISON + CASERNE',    6601,   'Souss-Massa', 'Inezgane Ait Melloul'),
    (7,  'SEC_HASSANIA',      'AL HASSANIA',              'AL HASSANIA',                    8520,   'Souss-Massa', 'Agadir'),
    (8,  'SEC_HOUDA_1',       'AL HOUDA 1',               'AL HOUDA 1',                     36366,  'Souss-Massa', 'Agadir'),
    (9,  'SEC_HOUDA_2',       'AL HOUDA 2',               'AL HOUDA 2',                     36562,  'Souss-Massa', 'Agadir'),
    (10, 'SEC_JIHADIA',       'AL JIHADIA',               'AL JIHADIA',                     74128,  'Souss-Massa', 'Inezgane Ait Melloul'),
    (11, 'SEC_MAGHRIB',       'AL MAGHRIB AL ARABI AM',   'AL MAGHRIB AL ARABI AIT MELLOU', 45753,  'Souss-Massa', 'Inezgane Ait Melloul'),
    (12, 'SEC_MASSIRA',       'AL MASSIRA',               'AL MASSIRA',                     27506,  'Souss-Massa', 'Agadir'),
    (13, 'SEC_AMICALES',      'Amicales',                 'Amicales',                       10434,  'Souss-Massa', 'Agadir'),
    (14, 'SEC_ANZA',          'ANZA',                     'ANZA',                           39357,  'Souss-Massa', 'Agadir'),
    (15, 'SEC_ANZA_OULYA',    'ANZA AL OULYA',            'ANZA AL OULYA',                  77185,  'Souss-Massa', 'Agadir'),
    (16, 'SEC_AOURIR',        'AOURIR',                   'AOURIR',                         77997,  'Souss-Massa', 'Agadir'),
    (17, 'SEC_ARGANA',        'ARGANA AIT MELLOUL',       'ARGANA AIT MELLOUL',             30980,  'Souss-Massa', 'Inezgane Ait Melloul'),
    (18, 'SEC_ARTISANAT',     'ARTISANAT 85',             'ARTISANAT 85',                   6165,   'Souss-Massa', 'Agadir'),
    (19, 'SEC_ASSAISS',       'ASSAISS YASMINA',          'ASSAISS + YASMINA',              69408,  'Souss-Massa', 'Inezgane Ait Melloul'),
    (20, 'SEC_ASSAKA',        'ASSAKA',                   'ASSAKA',                         21641,  'Souss-Massa', 'Agadir'),
    (21, 'SEC_ASSALAM',       'ASSALAM',                  'ASSALAM',                        28064,  'Souss-Massa', 'Agadir'),
    (22, 'SEC_AV_FAR',        'AV FAR TADDART',           'AV FAR TADDART',                 8712,   'Souss-Massa', 'Agadir'),
    (23, 'SEC_AV_2MARS',      'AVENUE 2 MARS',            'AVENUE 2 MARS',                  11590,  'Souss-Massa', 'Agadir'),
    (24, 'SEC_BENSERGAO',     'BENSERGAO',                'BENSEGAO',                       25099,  'Souss-Massa', 'Agadir'),
    (25, 'SEC_CENTRE_AZROU',  'CENTRE AZROU',             'CENTRE AZROU',                   63223,  'Souss-Massa', 'Inezgane Ait Melloul'),
    (26, 'SEC_CHOUHADA',      'CHOUHADA AL MOUSTAQBAL',   'CHOUHADA AL MOUSTAQBAL ADMIN',   47276,  'Souss-Massa', 'Agadir'),
    (27, 'SEC_CITE_SUISSE',   'CITE SUISSE',              'CITE SUISSE',                    6651,   'Souss-Massa', 'Agadir'),
    (28, 'SEC_CLINIQUE_JIH',  'CLINIQUE JIHANE',          'CLINIQUE JIHANE CITE SUISSE',    2882,   'Souss-Massa', 'Agadir'),
    (29, 'SEC_DAKHLA_1',      'DAKHLA 1',                 'DAKHLA 1',                       23814,  'Souss-Massa', 'Agadir'),
    (30, 'SEC_DAKHLA_2',      'DAKHLA 2',                 'DAKHLA 2',                       24012,  'Souss-Massa', 'Agadir'),
    (31, 'SEC_DAR_BOUBKER',   'DAR BOUBKER',              'DAR BOUBKER',                    304,    'Souss-Massa', 'Agadir'),
    (32, 'SEC_DCHEIRA',       'DCHEIRA',                  'DCHEIRA',                        93441,  'Souss-Massa', 'Inezgane Ait Melloul'),
    (33, 'SEC_DCHEIRA_200',   'Dcheira 200',              'Dcheira_200',                    41317,  'Souss-Massa', 'Inezgane Ait Melloul'),
    (34, 'SEC_DERB_MBAREK',   'Derb Mbarek',              'Derb Mbarek',                    33044,  'Souss-Massa', 'Agadir'),
    (35, 'SEC_DOUAR_SOUIRI',  'DOUAR SOUIRI',             'DOUAR SOUIRI',                   14118,  'Souss-Massa', 'Agadir'),
    (36, 'SEC_EL_FARAH',      'EL FARAH AL WIFAQ',        'EL FARAH AL WIFAQ',              83349,  'Souss-Massa', 'Agadir'),
    (37, 'SEC_EXT_DAKHLA_1',  'EXTENSION DAKHLA 1',       'EXTENSION DAKHLA 1',             9063,   'Souss-Massa', 'Agadir'),
    (38, 'SEC_EXT_DAKHLA_2',  'EXTENSION DAKHLA 2',       'EXTENSION DAKHLA 2',             10742,  'Souss-Massa', 'Agadir'),
    (39, 'SEC_FADESA',        'FADESA BNI ZNASSEN',       'FADESA BNI ZNASSEN',             17364,  'Souss-Massa', 'Inezgane Ait Melloul'),
    (40, 'SEC_FIDIYA',        'FIDIYA',                   'FIDIYA',                         3446,   'Souss-Massa', 'Agadir'),
    (41, 'SEC_FONTY_BAS',     'FONTY BAS',                'FONTY BAS',                      46965,  'Souss-Massa', 'Agadir'),
    (42, 'SEC_HAUT_FOUNTY',   'HAUT FOUNTY',              'HAUT FOUNTY',                    29315,  'Souss-Massa', 'Agadir'),
    (43, 'SEC_HAY_LAMZAR',    'HAY LAMZAR',               'HAY LAMZAR',                     85550,  'Souss-Massa', 'Inezgane Ait Melloul'),
    (44, 'SEC_HAYM1_NS',      'HAY MOHAMADI 1 NS',        'HAY MOHAMADI 1 NON STABILISE',   24441,  'Souss-Massa', 'Agadir'),
    (45, 'SEC_HAYM2_NS',      'HAY MOHAMADI 2 NS',        'HAY MOHAMADI 2 NON STABILISE',   7342,   'Souss-Massa', 'Agadir'),
    (46, 'SEC_HAYM_SAFAE',    'Hay Mohamadi SAFAE',       'Hay Mohamadi SAFAE',             8079,   'Souss-Massa', 'Agadir'),
    (47, 'SEC_HAYM_BAS',      'HAY MOHAMMADI BAS',        'HAY MOHAMMADI BAS',              65872,  'Souss-Massa', 'Agadir'),
    (48, 'SEC_HAYM_GHOFRANE', 'HAy Mohammadi GHOFRANE',   'HAy Mohammadi GHOFRANE',         11219,  'Souss-Massa', 'Agadir'),
    (49, 'SEC_HAYM_ISSLANE',  'HAY MOHAMMADI ISSLANE',    'HAY MOHAMMADI ISSLANE',          12185,  'Souss-Massa', 'Agadir'),
    (50, 'SEC_IGHIL_OUD',     'IGHIL OUDERDOUR',          'IGHIL OUDERDOUR',                7476,   'Souss-Massa', 'Agadir'),
    (51, 'SEC_IHCHACH',       'IHCHACH STABILISE',        'IHCHACH STABILISE',              22947,  'Souss-Massa', 'Agadir'),
    (52, 'SEC_IMM_NASSER',    'Imm Nasser Jet sakan',     'Imm Nasser Jet sakan',           5560,   'Souss-Massa', 'Agadir'),
    (53, 'SEC_INEZGANE',      'INEZGANE',                 'INEZGANE',                       45896,  'Souss-Massa', 'Inezgane Ait Melloul'),
    (54, 'SEC_JET_SAKAN',     'JET SAKAN',                'JET SAKAN',                      34971,  'Souss-Massa', 'Agadir'),
    (55, 'SEC_JORF',          'JORF',                     'JORF',                           39339,  'Souss-Massa', 'Inezgane Ait Melloul'),
    (56, 'SEC_LAHRACH',       'LAHRACH',                  'LAHRACH',                        29970,  'Souss-Massa', 'Inezgane Ait Melloul'),
    (57, 'SEC_LAHRACH_AGDAL', 'LAHRACH + AGDAL',          'LAHRACH + AGDAL Lakhyam Nejma',  27340,  'Souss-Massa', 'Inezgane Ait Melloul'),
    (58, 'SEC_LOT_ILLIGH',    'LOT ILLIGH',               'LOT ILLIGH',                     15236,  'Souss-Massa', 'Agadir'),
    (59, 'SEC_LOT_BIR_ANZ',   'LOTISSEMENT BIR ANZARANE', 'LOTISSEMENT BIR ANZARANE',       11032,  'Souss-Massa', 'Agadir'),
    (60, 'SEC_LOT_CHEMS',     'LOTISSEMENT CHEMS TIK',    'LOTISSEMENT CHEMS TIKIOUINE',    15516,  'Souss-Massa', 'Agadir'),
    (61, 'SEC_NAHDA',         'Nahda stabilise',          'Nahda_stabilisé',                22207,  'Souss-Massa', 'Agadir'),
    (62, 'SEC_OMRANE_85',     'OMRANE 85',                'OMRANE 85',                      5720,   'Souss-Massa', 'Agadir'),
    (63, 'SEC_PALAIS_ROYAL',  'Palais Royal Marjane',     'Palais Royal Marjane',           5479,   'Souss-Massa', 'Agadir'),
    (64, 'SEC_PARC_HAL',      'PARC HALIEUTIQUE',         'PARC HALIEUTIQUE',               32913,  'Souss-Massa', 'Agadir'),
    (65, 'SEC_QODS',          'QODS',                     'QODS',                           8127,   'Souss-Massa', 'Agadir'),
    (66, 'SEC_RIAD_SALAM',    'RIAD SALAM',               'RIAD SALAM',                     15943,  'Souss-Massa', 'Agadir'),
    (67, 'SEC_RMEL_TARRAST',  'RMEL TARRAST',             'RMEL TARRAST',                   95353,  'Souss-Massa', 'Inezgane Ait Melloul'),
    (68, 'SEC_29_FEV',        'SECTEUR 29 FEV',           'SECTEUR 29 FEV',                 31253,  'Souss-Massa', 'Agadir'),
    (69, 'SEC_AL_WAFA',       'SECTEUR AL WAFA',          'SECTEUR AL WAFA',                11116,  'Souss-Massa', 'Agadir'),
    (70, 'SEC_ANNAJAH',       'SECTEUR ANNAJAH',          'SECTEUR ANNAJAH',                8002,   'Souss-Massa', 'Agadir'),
    (71, 'SEC_BOUARG_LAKH',   'SECTEUR BOUARGANE LAKHIAM','SECTEUR BOUARGANE LAKHIAM',      76962,  'Souss-Massa', 'Agadir'),
    (72, 'SEC_CHARAF',        'SECTEUR CHARAF',           'SECTEUR CHARAF',                 14498,  'Souss-Massa', 'Agadir'),
    (73, 'SEC_HAY_HASSANI',   'SECTEUR HAY HASSANI',      'SECTEUR HAY HASSANI',            29991,  'Souss-Massa', 'Agadir'),
    (74, 'SEC_JACARANDA',     'SECTEUR JACARANDA',        'SECTEUR JACARANDA + AGHROUD',    27848,  'Souss-Massa', 'Agadir'),
    (75, 'SEC_LAGOUIRA',      'SECTEUR LAGOUIRA',         'SECTEUR LAGOUIRA',               9016,   'Souss-Massa', 'Agadir'),
    (76, 'SEC_TADDART_ANZA',  'TADDART ANZA',             'TADDART ANZA',                   26903,  'Souss-Massa', 'Agadir'),
    (77, 'SEC_TADOUART_TAG',  'TADOUART TAGADIRT',        'TADOUART TAGADIRT',              48627,  'Souss-Massa', 'Agadir'),
    (78, 'SEC_TAGHAZOUTE',    'TAGHAZOUTE',               'TAGHAZOUTE',                     20533,  'Souss-Massa', 'Agadir'),
    (79, 'SEC_TAMAZART',      'TAMAZART',                 'TAMAZART',                       29897,  'Souss-Massa', 'Inezgane Ait Melloul'),
    (80, 'SEC_TAMRAGHT',      'TAMRAGHT',                 'TAMRAGHT',                       29881,  'Souss-Massa', 'Agadir'),
    (81, 'SEC_TARIK_KHAYR',   'TARIK EL KHAYR',           'TARIK EL KHAYR',                 6054,   'Souss-Massa', 'Agadir'),
    (82, 'SEC_TIKIOUINE',     'TIKIOUINE',                'TIKIOUINE',                      34808,  'Souss-Massa', 'Agadir'),
    (83, 'SEC_TILILLA',       'TILILLA',                  'TILILLA',                        68360,  'Souss-Massa', 'Agadir'),
    (84, 'SEC_TIMIRSSIT',     'TIMIRSSIT + AZROU SUD',    'TIMIRSSIT + AZROU SUD',          16246,  'Souss-Massa', 'Inezgane Ait Melloul'),
    (85, 'SEC_TOUHMOU',       'TOUHMOU',                  'TOUHMOU',                        4343,   'Souss-Massa', 'Inezgane Ait Melloul'),
    (86, 'SEC_ZAITOUNE',      'ZAITOUNE',                 'ZAITOUNE',                       35237,  'Souss-Massa', 'Agadir'),
    (87, 'SEC_ZI_TASSILA_12', 'ZI TASSILA 1 et 2',        'ZI TASSILA 1&2',                 31509,  'Souss-Massa', 'Agadir'),
    (88, 'SEC_ZI_TASSILA_3',  'ZI TASSILA 3TR',           'ZI TASSILA 3TR',                 9880,   'Souss-Massa', 'Agadir'),
    (89, 'SEC_ZONE_HOP_COS',  'Zone Hopital COS',         'ZOne Hopital COS ONE Lycee Mar', 2172,   'Souss-Massa', 'Agadir'),
    (90, 'SEC_ZI_AM',         'ZONE INDUSTRIELLE AM',     'ZONE INDUSTRIELLE AM',           42665,  'Souss-Massa', 'Inezgane Ait Melloul')

ON CONFLICT (id_secteur) DO UPDATE
SET code_secteur            = EXCLUDED.code_secteur,
    nom_secteur             = EXCLUDED.nom_secteur,
    nom_secteur_hydraulique = EXCLUDED.nom_secteur_hydraulique,
    lineaire_m              = EXCLUDED.lineaire_m,
    nom_province            = EXCLUDED.nom_province;

-- Vérification
SELECT 
    COUNT(*) AS nb_secteurs,
    SUM(CASE WHEN nom_province = 'Agadir' THEN 1 ELSE 0 END) AS nb_agadir,
    SUM(CASE WHEN nom_province = 'Inezgane Ait Melloul' THEN 1 ELSE 0 END) AS nb_inezgane
FROM dwh.dim_secteur;