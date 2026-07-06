TRUNCATE TABLE gold.dim_type_reclamation CASCADE;

INSERT INTO gold.dim_type_reclamation 
    (code_type, libelle_reclamation, categorie_reclamation, 
     ligne_source_excel, est_comptage, est_duree, ordre_affichage)
VALUES
    ('FUIT_EAU',    'Fuite eau',                     'Reclamation_Technique',  25, TRUE,  FALSE, 1),
    ('MANQ_PRESS',  'Manque de pression',            'Reclamation_Technique',  26, TRUE,  FALSE, 2),
    ('MANQ_EAU',    'Manque d''eau',                 'Reclamation_Technique',  27, TRUE,  FALSE, 3),
    ('TPS_COUP',    'Temps moyen coupure',           'Reclamation_QoS',        28, FALSE, TRUE,  4),
    ('QUALITE',     'Qualite',                       'Reclamation_Qualite',    29, TRUE,  FALSE, 5),
    ('REFECTION',   'Refection',                     'Reclamation_Travaux',    30, TRUE,  FALSE, 6),
    ('AUTRES',      'Autres',                        'Reclamation_Divers',     31, TRUE,  FALSE, 7),
    ('INC_RESEAU',  'Incidents sur reseau',          'Incident',               32, TRUE,  FALSE, 8),
    ('INC_TIERS',   'Incidents causes par un tiers', 'Incident',               33, TRUE,  FALSE, 9),
    ('DELAI_TRAIT', 'Delai moyen traitement',        'QoS_Traitement',         34, FALSE, TRUE,  10);

SELECT COUNT(*) AS nb_types FROM gold.dim_type_reclamation;