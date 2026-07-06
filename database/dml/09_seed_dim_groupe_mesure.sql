TRUNCATE TABLE gold.dim_groupe_mesure CASCADE;

INSERT INTO gold.dim_groupe_mesure 
    (code_groupe, libelle_groupe, description, ordre_affichage)
VALUES
    ('SEC_AGD',        'SECTEURS AGADIR',             'Secteurs hydrauliques d''Agadir', 1),
    ('SEC_INZ',        'SECTEURS INEZGANE AM',        'Secteurs Inezgane Ait Melloul', 2),
    ('GROS_CONSO',     'GROS CONSO',                  'Gros consommateurs', 3),
    ('MODUL_PRESS',    'MODULATEURS DE PRESSION',     'Modulateurs de pression', 4),
    ('SORTIE_RES',     'SORTIES RESERVOIRS',          'Points de sortie des reservoirs', 5),
    ('ENTREE_RES',     'ENTREES RESERVOIRS',          'Points d''entree des reservoirs', 6),
    ('POINTS_PRESS',   'POINTS DE PRESSION',          'Points de mesure de pression', 7),
    ('AUTRES',         'AUTRES',                      'Autres points de mesure', 99);

SELECT * FROM gold.dim_groupe_mesure ORDER BY ordre_affichage;