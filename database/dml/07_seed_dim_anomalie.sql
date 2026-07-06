TRUNCATE TABLE gold.dim_anomalie_releve CASCADE;

INSERT INTO gold.dim_anomalie_releve 
    (code_anomalie, libelle_anomalie, description, est_normal)
VALUES
    ('N', 'Normal',              'Releve normal sans anomalie',                    TRUE),
    ('A', 'Anomalie compteur',   'Anomalie detectee sur le compteur',              FALSE),
    ('I', 'Inaccessible',        'Compteur inaccessible lors du releve',           FALSE),
    ('K', 'Compteur bloque',     'Compteur bloque ou en panne',                    FALSE);

SELECT * FROM gold.dim_anomalie_releve;