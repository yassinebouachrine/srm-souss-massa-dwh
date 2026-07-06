TRUNCATE TABLE gold.dim_province CASCADE;

INSERT INTO gold.dim_province (code_province, nom_province, id_region)
SELECT code, nom, (SELECT id_region FROM gold.dim_region WHERE code_region = 'SM')
FROM (VALUES
    ('AGD', 'Agadir'),
    ('CHT', 'Chtouka Ait Baha'),
    ('INZ', 'Inezgane Ait Melloul'),
    ('TAR', 'Taroudante'),
    ('TAT', 'Tata'),
    ('TIZ', 'Tiznit')
) AS t(code, nom);

SELECT * FROM gold.dim_province ORDER BY nom_province;