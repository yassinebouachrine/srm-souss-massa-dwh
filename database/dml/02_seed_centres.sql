-- ═══════════════════════════════════════════════════════════════
-- SEED — 68 centres de distribution
-- ═══════════════════════════════════════════════════════════════

-- ═══ DP TATA (12 centres) ═══
INSERT INTO app_staging.ref_centre (id_centre, code_centre, nom_centre, type_centre, id_province) VALUES
(1,  'C_TATA_01', 'Tata',                   'Principal',   1),
(2,  'C_TATA_02', 'Foum Zguid',             'Secondaire',  1),
(3,  'C_TATA_03', 'Ait Baha Mbarek',        'Secondaire',  1),
(4,  'C_TATA_04', 'Akka',                   'Secondaire',  1),
(5,  'C_TATA_05', 'Foum Lhssen',            'Secondaire',  1),
(6,  'C_TATA_06', 'Tissent',                'Secondaire',  1),
(7,  'C_TATA_07', 'Allougoum',              'Secondaire',  1),
(8,  'C_TATA_08', 'Issafen',                'Secondaire',  1),
(9,  'C_TATA_09', 'Akka Ighane',            'Secondaire',  1),
(10, 'C_TATA_10', 'Tigzmirte',              'Secondaire',  1),
(11, 'C_TATA_11', 'Ait Ouabelli',           'Secondaire',  1),
(12, 'C_TATA_12', 'Smira - Foum Zguid',     'Secondaire',  1)
ON CONFLICT (id_centre) DO NOTHING;

-- ═══ DP TIZNIT (15 centres) ═══
INSERT INTO app_staging.ref_centre (id_centre, code_centre, nom_centre, type_centre, id_province) VALUES
(13, 'C_TIZ_01', 'Tiznit',             'Principal',   2),
(14, 'C_TIZ_02', 'Tafraout',           'Secondaire',  2),
(15, 'C_TIZ_03', 'Aval Tiznit',        'Secondaire',  2),
(16, 'C_TIZ_04', 'Amont Tiznit',       'Secondaire',  2),
(17, 'C_TIZ_05', 'Talaint',            'Secondaire',  2),
(18, 'C_TIZ_06', 'Tizoughrane',        'Secondaire',  2),
(19, 'C_TIZ_07', 'Douars Talaint',     'Secondaire',  2),
(20, 'C_TIZ_08', 'Ammelne',            'Secondaire',  2),
(21, 'C_TIZ_09', 'Larbaa Sahel',       'Secondaire',  2),
(22, 'C_TIZ_10', 'Aglou',              'Secondaire',  2),
(23, 'C_TIZ_11', 'Tighmi',             'Secondaire',  2),
(24, 'C_TIZ_12', 'Zaouia',             'Secondaire',  2),
(25, 'C_TIZ_13', 'Lmaadar Lakbir',     'Secondaire',  2),
(26, 'C_TIZ_14', 'Anzi',               'Secondaire',  2),
(27, 'C_TIZ_15', 'Ras Mouka',          'Secondaire',  2)
ON CONFLICT (id_centre) DO NOTHING;

-- ═══ DP CHTOUKA AIT BAHA (13 centres) ═══
INSERT INTO app_staging.ref_centre (id_centre, code_centre, nom_centre, type_centre, id_province) VALUES
(28, 'C_CHT_01', 'Biougra',             'Principal',   3),
(29, 'C_CHT_02', 'Sidi Bibi',           'Secondaire',  3),
(30, 'C_CHT_03', 'Massa Douars',        'Secondaire',  3),
(31, 'C_CHT_04', 'Massa',               'Secondaire',  3),
(32, 'C_CHT_05', 'Ait Baha',            'Secondaire',  3),
(33, 'C_CHT_06', 'Ait Baha Douars',     'Secondaire',  3),
(34, 'C_CHT_07', 'Belfaa et Douars',    'Secondaire',  3),
(35, 'C_CHT_08', 'Ait Milk',            'Secondaire',  3),
(36, 'C_CHT_09', 'Ait Milk Douars',     'Secondaire',  3),
(37, 'C_CHT_10', 'Idaougnidif',         'Secondaire',  3),
(38, 'C_CHT_11', 'Douira',              'Secondaire',  3),
(39, 'C_CHT_12', 'Inchaden',            'Secondaire',  3),
(40, 'C_CHT_13', 'Ait Aamira',          'Secondaire',  3)
ON CONFLICT (id_centre) DO NOTHING;

-- ═══ DP TAROUDANT (11 centres) ═══
INSERT INTO app_staging.ref_centre (id_centre, code_centre, nom_centre, type_centre, id_province) VALUES
(41, 'C_TAR_01', 'Taroudant',                'Principal',   4),
(42, 'C_TAR_02', 'Ouled Teima',              'Secondaire',  4),
(43, 'C_TAR_03', 'Ouled Berhil',             'Secondaire',  4),
(44, 'C_TAR_04', 'Ait Iaaza',                'Secondaire',  4),
(45, 'C_TAR_05', 'Taliouine',                'Secondaire',  4),
(46, 'C_TAR_06', 'Laglalcha',                'Secondaire',  4),
(47, 'C_TAR_07', 'Aoulouz',                  'Secondaire',  4),
(48, 'C_TAR_08', 'Sidi El Guerdan',          'Secondaire',  4),
(49, 'C_TAR_09', 'Sidi Mohamed Lhamri',      'Secondaire',  4),
(50, 'C_TAR_10', 'Ighrem',                   'Secondaire',  4),
(51, 'C_TAR_11', 'Ait Addellah',             'Secondaire',  4)
ON CONFLICT (id_centre) DO NOTHING;

-- ═══ DP INEZGANE AIT MELLOUL (3 centres) ═══
INSERT INTO app_staging.ref_centre (id_centre, code_centre, nom_centre, type_centre, id_province) VALUES
(52, 'C_INZ_01', 'Lqliaa',              'Principal',   5),
(53, 'C_INZ_02', 'Temsia',              'Secondaire',  5),
(54, 'C_INZ_03', 'Ouled Dahhou',        'Secondaire',  5)
ON CONFLICT (id_centre) DO NOTHING;

-- ═══ DP AGADIR (14 centres) ═══
INSERT INTO app_staging.ref_centre (id_centre, code_centre, nom_centre, type_centre, id_province) VALUES
(55, 'C_AGA_01', 'Agadir (Ex-RAMSA)',        'Principal',   6),
(56, 'C_AGA_02', 'Drarga',                   'Secondaire',  6),
(57, 'C_AGA_03', 'Douars Drarga (Tamait)',   'Secondaire',  6),
(58, 'C_AGA_04', 'Amskroud',                 'Secondaire',  6),
(59, 'C_AGA_05', 'Douars Amskroud',          'Secondaire',  6),
(60, 'C_AGA_06', 'Douars Taghazout',         'Secondaire',  6),
(61, 'C_AGA_07', 'Taghazout',                'Secondaire',  6),
(62, 'C_AGA_08', 'Douars Immouzer',          'Secondaire',  6),
(63, 'C_AGA_09', 'Immouzer',                 'Secondaire',  6),
(64, 'C_AGA_10', 'Tamri',                    'Secondaire',  6),
(65, 'C_AGA_11', 'Douars Tamri',             'Secondaire',  6),
(66, 'C_AGA_12', 'Douars Imsouane',          'Secondaire',  6),
(67, 'C_AGA_13', 'Imsouane',                 'Secondaire',  6),
(68, 'C_AGA_14', 'Aziar',                    'Secondaire',  6)
ON CONFLICT (id_centre) DO NOTHING;