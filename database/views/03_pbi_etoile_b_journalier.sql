-- ═══════════════════════════════════════════════════════════════
-- VUES PBI — AGRÉGATS JOURNALIERS (Étoile B)
-- Pour les pages : DEBIT MIN PMAC, DEBIT MIN PCWIN, VOL JOURN
-- ═══════════════════════════════════════════════════════════════


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_DEBIT_MIN_JOURNALIER : Débit min/moy nocturne
-- Utilisé par pages : DEBIT MIN PMAC / PCWIN
-- Calcul à la volée depuis fait_mesure_temps_reel
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_debit_min_journalier AS
WITH debits_par_jour AS (
    SELECT
        f.id_point_mesure,
        f.id_source_mesure,
        f.canal,
        DATE(f.heure) AS date_jour,
        MIN(f.debit_m3_h) AS debit_min_jour,
        AVG(f.debit_m3_h) AS debit_moy_jour,
        MAX(f.debit_m3_h) AS debit_max_jour,
        COUNT(*) AS nb_mesures
    FROM dwh.fait_mesure_temps_reel f
    WHERE f.voie = 'DEBIT'
      AND f.debit_m3_h IS NOT NULL
      AND f.debit_m3_h >= 0
      AND f.qualite_donnees IN ('GOOD', 'SUSPECT')
    GROUP BY f.id_point_mesure, f.id_source_mesure, f.canal, DATE(f.heure)
    HAVING COUNT(*) >= 10  -- Au moins 10 mesures dans le jour
)
SELECT
    -- ─── Dimensions ───
    dp.id_pmac                        AS point_de_mesure,
    dp.nom_point,
    dp.groupe_mesure,
    ds.code_source                    AS source_systeme,
    d.canal,
    'DEBIT'                           AS voie,
    -- ─── Temps ───
    d.date_jour                       AS date,
    EXTRACT(YEAR FROM d.date_jour)::INT  AS annee,
    EXTRACT(MONTH FROM d.date_jour)::INT AS mois,
    EXTRACT(DAY FROM d.date_jour)::INT   AS jour,
    -- ─── Mesures ───
    ROUND(d.debit_min_jour::NUMERIC, 2) AS debit_min_jour_s,
    ROUND(d.debit_moy_jour::NUMERIC, 2) AS debit_moyen_jour_s,
    ROUND(d.debit_max_jour::NUMERIC, 2) AS debit_max_jour_s,
    -- ─── Pourcentage débit min / moy (indicateur clé) ───
    ROUND(
        CASE WHEN d.debit_moy_jour > 0 
             THEN (d.debit_min_jour / d.debit_moy_jour * 100)::NUMERIC
             ELSE NULL END, 2
    ) AS pct_min_sur_moy,
    -- ─── Nb mesures (contrôle qualité) ───
    d.nb_mesures,
    -- ─── Heure du débit min (utile) ───
    (SELECT f2.heure 
     FROM dwh.fait_mesure_temps_reel f2
     WHERE f2.id_point_mesure = d.id_point_mesure
       AND DATE(f2.heure) = d.date_jour
       AND f2.debit_m3_h = d.debit_min_jour
     LIMIT 1
    ) AS dateheure_debit_min
FROM debits_par_jour d
JOIN dwh.dim_point_mesure  dp ON d.id_point_mesure = dp.id_point_mesure
JOIN dwh.dim_source_mesure ds ON d.id_source_mesure = ds.id_source_mesure
WHERE dp.est_actif = TRUE;

COMMENT ON VIEW dwh.vw_pbi_debit_min_journalier IS 
    'Débit min/moy journalier — pages DEBIT MIN PMAC/PCWIN';


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_VOL_JOURNALIER : Volumes journaliers
-- Utilisé par pages : VOL JOURN PMAC / PCWIN
-- Calcule Index 08h et Volume Journalier (Index J+1 - Index J)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_vol_journalier AS
WITH index_08h AS (
    -- Index à 8h précis par jour (tolérance 15 min)
    SELECT DISTINCT ON (id_point_mesure, canal, DATE(heure))
        id_point_mesure,
        id_source_mesure,
        canal,
        DATE(heure) AS date_jour,
        heure,
        index_compteur AS index_valeur
    FROM dwh.fait_mesure_temps_reel
    WHERE voie = 'INDEX'
      AND index_compteur IS NOT NULL
      AND EXTRACT(HOUR FROM heure) = 8
      AND EXTRACT(MINUTE FROM heure) < 15
    ORDER BY id_point_mesure, canal, DATE(heure), heure
)
SELECT
    -- ─── Dimensions ───
    dp.id_pmac                         AS point_de_mesure,
    dp.nom_point,
    dp.groupe_mesure,
    ds.code_source                     AS source_systeme,
    i.canal,
    'INDEX'                            AS voie,
    -- ─── Temps ───
    i.date_jour                        AS date,
    EXTRACT(YEAR FROM i.date_jour)::INT  AS annee,
    EXTRACT(MONTH FROM i.date_jour)::INT AS mois,
    EXTRACT(DAY FROM i.date_jour)::INT   AS jour,
    TO_CHAR(i.date_jour, 'YYYY-MM')    AS annee_mois,
    -- ─── Index ───
    i.index_valeur                     AS index_08h,
    -- Index à 8h du lendemain
    (SELECT i2.index_valeur
     FROM index_08h i2
     WHERE i2.id_point_mesure = i.id_point_mesure
       AND i2.canal = i.canal
       AND i2.date_jour = i.date_jour + INTERVAL '1 day'
     LIMIT 1
    ) AS index_08h_j_plus1,
    -- ─── Volume journalier ───
    (SELECT i2.index_valeur - i.index_valeur
     FROM index_08h i2
     WHERE i2.id_point_mesure = i.id_point_mesure
       AND i2.canal = i.canal
       AND i2.date_jour = i.date_jour + INTERVAL '1 day'
     LIMIT 1
    ) AS volume_journalier_m3
FROM index_08h i
JOIN dwh.dim_point_mesure  dp ON i.id_point_mesure = dp.id_point_mesure
JOIN dwh.dim_source_mesure ds ON i.id_source_mesure = ds.id_source_mesure
WHERE dp.est_actif = TRUE;

COMMENT ON VIEW dwh.vw_pbi_vol_journalier IS 
    'Volume journalier calculé depuis Index 08h — pages VOL JOURN PMAC/PCWIN';