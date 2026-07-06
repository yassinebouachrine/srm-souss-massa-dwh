-- ============================================================
-- Fichier : 01_seed_dim_temps.sql
-- Projet  : SRM Souss-Massa DWH
-- Date    : Juillet 2026
-- ============================================================

-- TODO: Ajouter les instructions SQL ici
-- ============================================================
-- Seed : DIM_TEMPS de 2020 a 2030 (4018 jours)
-- ============================================================

TRUNCATE TABLE gold.dim_temps CASCADE;

INSERT INTO gold.dim_temps (
    id_temps, date_complete, jour, jour_semaine, nom_jour,
    semaine_annee, mois, nom_mois, mois_annee,
    trimestre, nom_trimestre, semestre, annee,
    saison, est_weekend, est_jour_ferie, est_fin_mois,
    nb_jours_dans_mois
)
SELECT
    TO_CHAR(d, 'YYYYMMDD')::INTEGER AS id_temps,
    d AS date_complete,
    EXTRACT(DAY FROM d)::INTEGER AS jour,
    EXTRACT(ISODOW FROM d)::INTEGER AS jour_semaine,
    CASE EXTRACT(ISODOW FROM d)
        WHEN 1 THEN 'Lundi'
        WHEN 2 THEN 'Mardi'
        WHEN 3 THEN 'Mercredi'
        WHEN 4 THEN 'Jeudi'
        WHEN 5 THEN 'Vendredi'
        WHEN 6 THEN 'Samedi'
        WHEN 7 THEN 'Dimanche'
    END AS nom_jour,
    EXTRACT(WEEK FROM d)::INTEGER AS semaine_annee,
    EXTRACT(MONTH FROM d)::INTEGER AS mois,
    CASE EXTRACT(MONTH FROM d)
        WHEN 1 THEN 'Janvier'
        WHEN 2 THEN 'Fevrier'
        WHEN 3 THEN 'Mars'
        WHEN 4 THEN 'Avril'
        WHEN 5 THEN 'Mai'
        WHEN 6 THEN 'Juin'
        WHEN 7 THEN 'Juillet'
        WHEN 8 THEN 'Aout'
        WHEN 9 THEN 'Septembre'
        WHEN 10 THEN 'Octobre'
        WHEN 11 THEN 'Novembre'
        WHEN 12 THEN 'Decembre'
    END AS nom_mois,
    TO_CHAR(d, 'YYYY-MM') AS mois_annee,
    EXTRACT(QUARTER FROM d)::INTEGER AS trimestre,
    'T' || EXTRACT(QUARTER FROM d)::TEXT AS nom_trimestre,
    CASE WHEN EXTRACT(MONTH FROM d) <= 6 THEN 1 ELSE 2 END AS semestre,
    EXTRACT(YEAR FROM d)::INTEGER AS annee,
    CASE 
        WHEN EXTRACT(MONTH FROM d) IN (12, 1, 2) THEN 'Hiver'
        WHEN EXTRACT(MONTH FROM d) IN (3, 4, 5) THEN 'Printemps'
        WHEN EXTRACT(MONTH FROM d) IN (6, 7, 8) THEN 'Ete'
        WHEN EXTRACT(MONTH FROM d) IN (9, 10, 11) THEN 'Automne'
    END AS saison,
    EXTRACT(ISODOW FROM d) IN (6, 7) AS est_weekend,
    FALSE AS est_jour_ferie,
    d = (DATE_TRUNC('MONTH', d) + INTERVAL '1 MONTH - 1 day')::DATE AS est_fin_mois,
    EXTRACT(DAY FROM (DATE_TRUNC('MONTH', d) + INTERVAL '1 MONTH - 1 day'))::INTEGER AS nb_jours_dans_mois
FROM generate_series(
    '2020-01-01'::DATE,
    '2030-12-31'::DATE,
    '1 day'::INTERVAL
) d;

SELECT 
    MIN(date_complete) AS date_min,
    MAX(date_complete) AS date_max,
    COUNT(*) AS nb_jours
FROM gold.dim_temps;