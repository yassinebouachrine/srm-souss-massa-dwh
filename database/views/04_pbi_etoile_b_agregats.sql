-- ═══════════════════════════════════════════════════════════════
-- VUES PBI — AGRÉGATIONS SPÉCIALISÉES (Étoile B)
-- Pour les pages : Modulateurs, Bilan Réservoir, Points Groupés
-- ═══════════════════════════════════════════════════════════════


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_MODULATEURS_PRESSION
-- Pression amont/aval superposées pour les modulateurs
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_modulateurs_pression AS
SELECT
    -- ─── Point de mesure ───
    dp.id_point_mesure,
    dp.id_pmac,
    dp.nom_point                       AS point_de_mesure,
    dp.groupe_mesure,
    -- ─── Temps ───
    f.heure,
    DATE(f.heure)                      AS date_mesure,
    -- ─── Pressions ───
    f.pression_amont_bar               AS pression_amont,
    f.pression_aval_bar                AS pression_aval,
    f.pression_bar                     AS pression,
    -- Delta amont - aval (indicateur clé pour modulateurs)
    (f.pression_amont_bar - f.pression_aval_bar) AS delta_pression,
    -- ─── Qualité ───
    f.qualite_donnees,
    f.canal
FROM dwh.fait_mesure_temps_reel f
JOIN dwh.dim_point_mesure dp ON f.id_point_mesure = dp.id_point_mesure
WHERE dp.est_modulateur = TRUE
  AND f.voie = 'PRESSION'
  AND (f.pression_amont_bar IS NOT NULL OR f.pression_aval_bar IS NOT NULL);

COMMENT ON VIEW dwh.vw_pbi_modulateurs_pression IS 
    'Pressions amont/aval des modulateurs — page Modulateurs de Pression';


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_BILAN_MENSUEL_RESERVOIR
-- Volumes mensuels par réservoir
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_bilan_mensuel_reservoir AS
WITH volume_debut_fin_mois AS (
    -- Premier index du mois
    SELECT DISTINCT ON (id_point_mesure, EXTRACT(YEAR FROM heure), EXTRACT(MONTH FROM heure))
        id_point_mesure,
        DATE_TRUNC('month', heure)::DATE AS mois_debut,
        heure                            AS heure_debut,
        index_compteur                   AS index_debut
    FROM dwh.fait_mesure_temps_reel
    WHERE voie = 'INDEX' AND index_compteur IS NOT NULL
    ORDER BY id_point_mesure, EXTRACT(YEAR FROM heure), EXTRACT(MONTH FROM heure), heure ASC
)
SELECT
    dp.id_pmac                         AS pmac_id,
    dp.nom_point,
    dp.groupe_mesure,
    v.mois_debut                       AS date_mois,
    EXTRACT(YEAR FROM v.mois_debut)::INT  AS annee,
    EXTRACT(MONTH FROM v.mois_debut)::INT AS mois,
    TO_CHAR(v.mois_debut, 'YYYY-MM')   AS annee_mois,
    v.index_debut,
    -- Index fin de mois (premier du mois suivant)
    (SELECT v2.index_debut 
     FROM volume_debut_fin_mois v2
     WHERE v2.id_point_mesure = v.id_point_mesure
       AND v2.mois_debut = v.mois_debut + INTERVAL '1 month'
    ) AS index_fin,
    -- Volume mensuel
    (SELECT v2.index_debut - v.index_debut
     FROM volume_debut_fin_mois v2
     WHERE v2.id_point_mesure = v.id_point_mesure
       AND v2.mois_debut = v.mois_debut + INTERVAL '1 month'
    ) AS volume_mois
FROM volume_debut_fin_mois v
JOIN dwh.dim_point_mesure dp ON v.id_point_mesure = dp.id_point_mesure
WHERE dp.est_reservoir = TRUE;

COMMENT ON VIEW dwh.vw_pbi_bilan_mensuel_reservoir IS 
    'Volumes mensuels par réservoir — page Bilan Mensuel Réservoir';


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_BILAN_INDEX_PERIODE
-- Calcul volume par période personnalisée
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_bilan_index_periode AS
SELECT
    dp.id_pmac                         AS pmac_id,
    dp.nom_point                       AS point_de_mesure,
    dp.groupe_mesure,
    f.canal,
    DATE(f.heure)                      AS date,
    f.heure,
    f.index_compteur                   AS index_valeur,
    ds.code_source
FROM dwh.fait_mesure_temps_reel f
JOIN dwh.dim_point_mesure  dp ON f.id_point_mesure = dp.id_point_mesure
JOIN dwh.dim_source_mesure ds ON f.id_source_mesure = ds.id_source_mesure
WHERE f.voie = 'INDEX'
  AND f.index_compteur IS NOT NULL
  AND dp.est_actif = TRUE;

COMMENT ON VIEW dwh.vw_pbi_bilan_index_periode IS 
    'Index par période personnalisée — page Bilan Index Période';


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_POINTS_GROUPES : Agrégation par groupes métier
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_points_groupes AS
SELECT
    dgp.nom_groupe                     AS groupe,
    dgp.description_groupe,
    dgp.ordre_affichage                AS ordre,
    f.heure,
    DATE(f.heure)                      AS date_mesure,
    -- Somme pondérée par coefficient (généralement 1.0)
    SUM(f.debit_m3_h * bgp.coefficient) AS debit_agrege,
    SUM(f.pression_bar * bgp.coefficient) AS pression_agregee,
    SUM(f.index_compteur * bgp.coefficient) AS index_agrege,
    SUM(f.volume_15min * bgp.coefficient) AS volume_agrege,
    COUNT(DISTINCT f.id_point_mesure)  AS nb_points_agregation,
    f.voie
FROM dwh.fait_mesure_temps_reel f
JOIN dwh.bridge_groupe_point bgp ON f.id_point_mesure = bgp.id_point_mesure
JOIN dwh.dim_groupe_points dgp   ON bgp.id_groupe_points = dgp.id_groupe_points
WHERE dgp.est_actif = TRUE
GROUP BY dgp.nom_groupe, dgp.description_groupe, dgp.ordre_affichage, f.heure, DATE(f.heure), f.voie;

COMMENT ON VIEW dwh.vw_pbi_points_groupes IS 
    'Agrégation débit/pression/index par groupe métier — page Points Groupés';


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_PSEUDO_RENDEMENT_ETAGE
-- Pseudo-rendement basé sur débit min / débit moy
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_pseudo_rendement AS
WITH debits_mensuels AS (
    SELECT
        f.id_point_mesure,
        f.id_source_mesure,
        DATE_TRUNC('month', f.heure)::DATE AS mois_debut,
        AVG(daily_stats.debit_min) AS debit_min_moyen_mensuel,
        AVG(daily_stats.debit_moy) AS debit_moy_mensuel
    FROM dwh.fait_mesure_temps_reel f
    JOIN (
        SELECT 
            id_point_mesure,
            DATE(heure) AS date_jour,
            MIN(debit_m3_h) AS debit_min,
            AVG(debit_m3_h) AS debit_moy
        FROM dwh.fait_mesure_temps_reel
        WHERE voie = 'DEBIT' AND debit_m3_h IS NOT NULL AND debit_m3_h > 0
        GROUP BY id_point_mesure, DATE(heure)
    ) daily_stats ON f.id_point_mesure = daily_stats.id_point_mesure 
                  AND DATE(f.heure) = daily_stats.date_jour
    WHERE f.voie = 'DEBIT'
    GROUP BY f.id_point_mesure, f.id_source_mesure, DATE_TRUNC('month', f.heure)::DATE
)
SELECT
    dp.id_pmac                         AS point_mesure_regroupe,
    dp.nom_point,
    dp.groupe_mesure,
    ds.code_source                     AS source_systeme,
    dm.mois_debut,
    EXTRACT(YEAR FROM dm.mois_debut)::INT  AS annee,
    EXTRACT(MONTH FROM dm.mois_debut)::INT AS mois,
    ROUND(dm.debit_min_moyen_mensuel::NUMERIC, 2) AS debit_min_moyen_mensuel_sorties_reservoirs_etage,
    ROUND(dm.debit_moy_mensuel::NUMERIC, 2)        AS debit_moyen_mensuel_sorties_reservoirs_etage,
    ROUND(
        CASE WHEN dm.debit_moy_mensuel > 0
             THEN (dm.debit_min_moyen_mensuel / dm.debit_moy_mensuel * 100)::NUMERIC
             ELSE NULL END, 2
    ) AS pct_debit_min_sur_moyen,
    -- Pseudo-rendement = 100 - (débit_min / débit_moy * 100)
    ROUND(
        CASE WHEN dm.debit_moy_mensuel > 0
             THEN (100 - (dm.debit_min_moyen_mensuel / dm.debit_moy_mensuel * 100))::NUMERIC
             ELSE NULL END, 2
    ) AS pseudo_rendement
FROM debits_mensuels dm
JOIN dwh.dim_point_mesure  dp ON dm.id_point_mesure = dp.id_point_mesure
JOIN dwh.dim_source_mesure ds ON dm.id_source_mesure = ds.id_source_mesure
WHERE dp.est_reservoir = TRUE;

COMMENT ON VIEW dwh.vw_pbi_pseudo_rendement IS 
    'Pseudo-rendement mensuel par étage — page Pseudo Rendement / Étage';