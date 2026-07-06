TRUNCATE TABLE gold.dim_type_mesure CASCADE;

INSERT INTO gold.dim_type_mesure 
    (code_type, libelle_type, unite_defaut, description)
VALUES
    ('DEBIT',    'Debit horaire',        'm3/h',    'Mesure de debit cumule horaire (cum/hr)'),
    ('INDEX',    'Index compteur',       'm3',      'Index cumule du compteur'),
    ('PRESSION', 'Pression',             'm',       'Mesure de pression (metres ou bar)'),
    ('AMOUNT',   'Volume/Quantite',      'm3',      'Volume ou quantite mesuree'),
    ('NIVEAU',   'Niveau (reservoir)',   'm',       'Niveau d''eau dans reservoir'),
    ('ALARM',    'Alarme systeme',       NULL,      'Evenement d''alarme');

SELECT * FROM gold.dim_type_mesure;