TRUNCATE TABLE gold.dim_region CASCADE;

INSERT INTO gold.dim_region (code_region, nom_region, pays) VALUES
    ('SM', 'Souss-Massa', 'Maroc');

SELECT * FROM gold.dim_region;