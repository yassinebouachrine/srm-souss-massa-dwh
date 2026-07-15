-- ═══════════════════════════════════════════════════════════════
-- SEED — Types d'indicateurs de performance DP
-- Réorganisés par catégorie et fréquence de mise à jour
-- ═══════════════════════════════════════════════════════════════

-- Vider et réinitialiser
TRUNCATE TABLE app_staging.ref_type_indicateur RESTART IDENTITY CASCADE;

INSERT INTO app_staging.ref_type_indicateur
    (code_indicateur, libelle_indicateur, unite, categorie, ordre_affichage, est_actif)
VALUES
-- ═══ Commercial (mensuel) ═══
('NB_CLI',      'Nombre clients',                       'U',    'Commercial',        1,  TRUE),
('VENTE',       'Ventes',                                'm3',   'Commercial',        2,  TRUE),
('ACHAT',       'Achats',                                'm3',   'Commercial',        3,  TRUE),
('AUTOPROD',    'Autoproduction',                       'm3',   'Commercial',        4,  TRUE),
('CESSION',     'Cession',                              'm3',   'Commercial',        5,  TRUE),
('AGE_CPT',     'Age moyen compteurs Eau',              'An',   'Commercial',        6,  TRUE),

-- ═══ Fraudes (mensuel) ═══
('NB_FRAUD',    'Nombre de fraudes Eau',                'U',    'Fraudes',           10, TRUE),
('VOL_FRAUD',   'Volume Fraudes',                        'm3',   'Fraudes',           11, TRUE),

-- ═══ Performance (mensuel) ═══
('REND',        'Rendement',                             '%',    'Performance',       20, TRUE),
('ILP',         'Ilp',                                   'm3/Jr/KM', 'Performance',   21, TRUE),

-- ═══ Maintenance (mensuel) ═══
('RECH_FUITE',  'Recherche de fuites',                   'km',   'Maintenance',       30, TRUE),
('FUITE_CDT',   'Fuites sur cdt / PS',                   'U',    'Maintenance',       31, TRUE),
('FUITE_BRT',   'Fuites sur Brt',                        'U',    'Maintenance',       32, TRUE),
('FUITE_CPT',   'Fuites compteurs/ PS',                  'U',    'Maintenance',       33, TRUE),

-- ═══ Renouvellement (mensuel) ═══
('RES_RENOUV',  'Réseau renouvelé',                      'Km',   'Renouvellement',    40, TRUE),
('BRT_RENOUV',  'Branchements renouvelé',               'U',    'Renouvellement',    41, TRUE),
('CPT_RENOUV',  'Compteurs renouvelés',                 'U',    'Renouvellement',    42, TRUE),

-- ═══ Infrastructure (STATIQUE - Annuel ou rare) ═══
('LIN_RES',     'Linéaire réseau',                       'Km',   'Infrastructure',    90, TRUE),
('REDUCT_PRES', 'Réducteurs de pression',               'U',    'Infrastructure',    91, TRUE),
('SECT_HYD',    'Secteurs hydrauliques',                'U',    'Infrastructure',    92, TRUE),
('ETAGE_PRES',  'Etages de pression',                    'U',    'Infrastructure',    93, TRUE)
ON CONFLICT (code_indicateur) DO UPDATE
SET libelle_indicateur = EXCLUDED.libelle_indicateur,
    unite = EXCLUDED.unite,
    categorie = EXCLUDED.categorie,
    ordre_affichage = EXCLUDED.ordre_affichage;