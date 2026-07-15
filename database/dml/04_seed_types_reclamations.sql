-- ═══════════════════════════════════════════════════════════════
-- SEED — Types de réclamations
-- ═══════════════════════════════════════════════════════════════

INSERT INTO app_staging.ref_type_reclamation
    (code_type, libelle_reclamation, categorie_reclamation, est_comptage, est_duree, ordre_affichage)
VALUES
-- Incidents réseau
('INC_RESEAU',      'Incidents sur réseau',              'Incident',           TRUE,  TRUE,  1),
('INC_TIERS',       'Incidents causés par un tiers',     'Incident',           TRUE,  TRUE,  2),
-- Qualité traitement
('DELAI_TRAIT',     'Délai moyen traitement',            'QoS_Traitement',     FALSE, TRUE,  3),
-- Réclamations diverses (permet ajout personnalisé)
('AUTRES',          'Autres',                            'Reclamation_Divers', TRUE,  FALSE, 4),
-- Qualité service
('QUAL_EAU',        'Qualité eau',                       'Reclamation_QoS',    TRUE,  FALSE, 5),
('QUAL_PRESSION',   'Qualité pression',                  'Reclamation_QoS',    TRUE,  FALSE, 6),
-- Facturation
('FACT_ERREUR',     'Erreurs de facturation',            'Reclamation_Facturation', TRUE, FALSE, 7),
('FACT_CONTEST',    'Contestations',                     'Reclamation_Facturation', TRUE, FALSE, 8),
-- Compteur
('CPT_DEFAILLANT',  'Compteur défaillant',               'Reclamation_Compteur',    TRUE, FALSE, 9),
('CPT_RELEVE',      'Problème relevé',                   'Reclamation_Compteur',    TRUE, FALSE, 10)
ON CONFLICT (code_type) DO UPDATE
SET libelle_reclamation = EXCLUDED.libelle_reclamation,
    categorie_reclamation = EXCLUDED.categorie_reclamation,
    est_comptage = EXCLUDED.est_comptage,
    est_duree = EXCLUDED.est_duree,
    ordre_affichage = EXCLUDED.ordre_affichage;