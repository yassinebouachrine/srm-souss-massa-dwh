TRUNCATE TABLE gold.dim_heure CASCADE;

INSERT INTO gold.dim_heure (
    id_heure, heure, minute, heure_minute,
    tranche_horaire, periode_journee,
    est_heure_pointe, est_heure_nuit
)
SELECT
    h AS id_heure,
    h AS heure,
    0 AS minute,
    LPAD(h::TEXT, 2, '0') || ':00' AS heure_minute,
    LPAD(h::TEXT, 2, '0') || 'h-' || LPAD((h+1)::TEXT, 2, '0') || 'h' AS tranche_horaire,
    CASE 
        WHEN h BETWEEN 0 AND 5 THEN 'Nuit'
        WHEN h BETWEEN 6 AND 11 THEN 'Matin'
        WHEN h BETWEEN 12 AND 17 THEN 'Apres-midi'
        WHEN h BETWEEN 18 AND 23 THEN 'Soir'
    END AS periode_journee,
    h IN (7, 8, 9, 18, 19, 20) AS est_heure_pointe,
    h BETWEEN 0 AND 5 AS est_heure_nuit
FROM generate_series(0, 23) AS h;

SELECT COUNT(*) AS nb_heures FROM gold.dim_heure;