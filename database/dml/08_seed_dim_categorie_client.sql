TRUNCATE TABLE gold.dim_categorie_client CASCADE;

INSERT INTO gold.dim_categorie_client 
    (code_categorie, libelle_categorie, description)
VALUES
    ('A', 'Domestique',            'Clients domestiques / residentiels'),
    ('G', 'Gros consommateur',     'Grands comptes, industries'),
    ('B', 'Bornes fontaines',      'Bornes fontaines publiques'),
    ('D', 'Administration',        'Administrations publiques'),
    ('P', 'Preferentiel',          'Tarif preferentiel');

SELECT * FROM gold.dim_categorie_client;