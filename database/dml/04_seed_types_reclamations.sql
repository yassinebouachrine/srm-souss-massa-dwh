-- ═══════════════════════════════════════════════════════════════
-- SEED — Types de réclamations (alignés sur Excel "Réclamations eau")
-- ═══════════════════════════════════════════════════════════════

TRUNCATE TABLE app_staging.ref_type_reclamation RESTART IDENTITY CASCADE;

INSERT INTO app_staging.ref_type_reclamation
    (code_type, libelle_reclamation, categorie_reclamation, est_comptage, est_duree, ordre_affichage)
VALUES
-- ── Réclamations liées à l'eau (comptage) ──
('FUITE_EAU',       'Fuite eau',                     'Reclamation_Eau',      TRUE,  FALSE, 1),
('MANQUE_PRESSION', 'Manque de pression',            'Reclamation_Eau',      TRUE,  FALSE, 2),
('MANQUE_EAU',      'Manque d''eau',                 'Reclamation_Eau',      TRUE,  FALSE, 3),
('QUALITE',         'Qualité',                       'Reclamation_Eau',      TRUE,  FALSE, 4),
('REFECTION',       'Réfection',                     'Reclamation_Eau',      TRUE,  FALSE, 5),

-- ── Incidents réseau (comptage) ──
('INC_RESEAU',      'Incidents sur réseau',          'Incidents',            TRUE,  FALSE, 6),
('INC_TIERS',       'Incidents causés par un tiers', 'Incidents',            TRUE,  FALSE, 7),

-- ── Indicateurs de qualité de service (durée) ──
('TEMPS_COUPURE',   'Temps moy coupure (h)',         'QoS_Traitement',       FALSE, TRUE,  8),
('DELAI_TRAIT',     'Délai moy traitement (j)',      'QoS_Traitement',       FALSE, TRUE,  9),

-- ── Fourre-tout (uniquement pour compatibilité fichiers Excel legacy) ──
('AUTRES',          'Autres',                        'Reclamation_Divers',   TRUE,  FALSE, 10)

ON CONFLICT (code_type) DO UPDATE
SET libelle_reclamation   = EXCLUDED.libelle_reclamation,
    categorie_reclamation = EXCLUDED.categorie_reclamation,
    est_comptage          = EXCLUDED.est_comptage,
    est_duree             = EXCLUDED.est_duree,
    ordre_affichage       = EXCLUDED.ordre_affichage;