-- ═══════════════════════════════════════════════════════════════
-- VUE MATERIALISEE — CARTE ENRICHIE (demande encadrant)
-- 
-- Objectif : Afficher SUR LA CARTE pour chaque point de mesure :
--   - Nom, groupe, coordonnees
--   - DERNIERES valeurs Debit / Pression / Index / Volume
--   - Timestamp de la derniere mesure
--   - Statut qualite
--   - Info agregees (moyenne 7 derniers jours)
-- 
-- Refresh : a programmer via Airflow (toutes les heures)
--   REFRESH MATERIALIZED VIEW CONCURRENTLY dwh.vw_pbi_carte_points_enrichie;
-- ═══════════════════════════════════════════════════════════════

DROP MATERIALIZED VIEW IF EXISTS dwh.vw_pbi_carte_points_enrichie CASCADE;

CREATE MATERIALIZED VIEW dwh.vw_pbi_carte_points_enrichie AS
WITH 
-- Derniere mesure de DEBIT par point
last_debit AS (
    SELECT DISTINCT ON (id_point_mesure)
        id_point_mesure,
        debit_m3_h            AS derniere_valeur_debit,
        heure                 AS derniere_heure_debit,
        qualite_donnees       AS qualite_debit,
        canal                 AS canal_debit
    FROM dwh.fait_mesure_temps_reel
    WHERE voie = 'DEBIT' AND debit_m3_h IS NOT NULL
    ORDER BY id_point_mesure, heure DESC
),
-- Derniere mesure de PRESSION par point
last_pression AS (
    SELECT DISTINCT ON (id_point_mesure)
        id_point_mesure,
        COALESCE(pression_bar, pression_amont_bar, pression_aval_bar) AS derniere_valeur_pression,
        pression_amont_bar    AS derniere_pression_amont,
        pression_aval_bar     AS derniere_pression_aval,
        heure                 AS derniere_heure_pression,
        qualite_donnees       AS qualite_pression
    FROM dwh.fait_mesure_temps_reel
    WHERE voie = 'PRESSION' 
      AND (pression_bar IS NOT NULL 
           OR pression_amont_bar IS NOT NULL 
           OR pression_aval_bar IS NOT NULL)
    ORDER BY id_point_mesure, heure DESC
),
-- Derniere mesure d'INDEX par point
last_index AS (
    SELECT DISTINCT ON (id_point_mesure)
        id_point_mesure,
        index_compteur        AS derniere_valeur_index,
        heure                 AS derniere_heure_index,
        qualite_donnees       AS qualite_index
    FROM dwh.fait_mesure_temps_reel
    WHERE voie = 'INDEX' AND index_compteur IS NOT NULL
    ORDER BY id_point_mesure, heure DESC
),
-- Derniere mesure de VOLUME par point
last_volume AS (
    SELECT DISTINCT ON (id_point_mesure)
        id_point_mesure,
        volume_15min          AS derniere_valeur_volume,
        heure                 AS derniere_heure_volume
    FROM dwh.fait_mesure_temps_reel
    WHERE voie = 'VOLUME' AND volume_15min IS NOT NULL
    ORDER BY id_point_mesure, heure DESC
),
-- Statistiques 7 derniers jours (moyennes)
stats_7j AS (
    SELECT 
        id_point_mesure,
        AVG(debit_m3_h)             FILTER (WHERE voie = 'DEBIT')        AS debit_moyen_7j,
        MIN(debit_m3_h)             FILTER (WHERE voie = 'DEBIT')        AS debit_min_7j,
        MAX(debit_m3_h)             FILTER (WHERE voie = 'DEBIT')        AS debit_max_7j,
        AVG(pression_bar)           FILTER (WHERE voie = 'PRESSION')     AS pression_moyenne_7j,
        MIN(pression_bar)           FILTER (WHERE voie = 'PRESSION')     AS pression_min_7j,
        MAX(pression_bar)           FILTER (WHERE voie = 'PRESSION')     AS pression_max_7j,
        COUNT(*)                                                          AS nb_mesures_7j,
        COUNT(*) FILTER (WHERE qualite_donnees = 'GOOD')                 AS nb_mesures_good_7j,
        COUNT(*) FILTER (WHERE qualite_donnees = 'SUSPECT')              AS nb_mesures_suspect_7j
    FROM dwh.fait_mesure_temps_reel
    WHERE heure >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY id_point_mesure
),
-- Libelle metier canal (si disponible)
canal_labels AS (
    SELECT 
        id_pmac,
        STRING_AGG(canal_label, ' | ' ORDER BY canal) AS labels_canaux
    FROM dwh.dim_canal_label
    GROUP BY id_pmac
),
-- Groupes d'appartenance
groupes_points AS (
    SELECT 
        bgp.id_point_mesure,
        STRING_AGG(dgp.nom_groupe, ' | ' ORDER BY dgp.nom_groupe) AS noms_groupes
    FROM dwh.bridge_groupe_point bgp
    JOIN dwh.dim_groupe_points dgp ON bgp.id_groupe_points = dgp.id_groupe_points
    GROUP BY bgp.id_point_mesure
)
SELECT
    -- Identifiants
    dp.id_point_mesure,
    dp.id_pmac,
    dp.nom_point,
    dp.station_pcwin,
    -- Groupe et categorie
    dp.groupe_mesure,
    gp.noms_groupes,
    -- Geolocalisation
    dp.latitude,
    dp.longitude,
    dp.cote_altitude,
    dp.capacite_reservoir_m3,
    -- Source
    ds.code_source,
    ds.libelle_source,
    -- Flags capacites
    dp.est_pression,
    dp.est_debit,
    dp.est_reservoir,
    dp.est_modulateur,
    dp.est_amont,
    dp.est_aval,
    -- Type point (pour icone)
    CASE
        WHEN dp.est_modulateur   THEN 'Modulateur'
        WHEN dp.est_reservoir    THEN 'Reservoir'
        WHEN dp.est_pression     THEN 'Pression'
        WHEN dp.est_debit        THEN 'Debit'
        ELSE 'Autre'
    END AS type_point,
    -- Libelles canaux metier
    cl.labels_canaux,
    -- DERNIERE MESURE DEBIT
    ld.derniere_valeur_debit,
    ld.derniere_heure_debit,
    ld.qualite_debit,
    -- DERNIERE MESURE PRESSION
    lp.derniere_valeur_pression,
    lp.derniere_pression_amont,
    lp.derniere_pression_aval,
    lp.derniere_heure_pression,
    lp.qualite_pression,
    -- DERNIERE MESURE INDEX
    li.derniere_valeur_index,
    li.derniere_heure_index,
    li.qualite_index,
    -- DERNIERE MESURE VOLUME
    lv.derniere_valeur_volume,
    lv.derniere_heure_volume,
    -- Statistiques 7 derniers jours
    ROUND(s7.debit_moyen_7j::NUMERIC, 2)      AS debit_moyen_7j,
    ROUND(s7.debit_min_7j::NUMERIC, 2)        AS debit_min_7j,
    ROUND(s7.debit_max_7j::NUMERIC, 2)        AS debit_max_7j,
    ROUND(s7.pression_moyenne_7j::NUMERIC, 2) AS pression_moyenne_7j,
    ROUND(s7.pression_min_7j::NUMERIC, 2)     AS pression_min_7j,
    ROUND(s7.pression_max_7j::NUMERIC, 2)     AS pression_max_7j,
    s7.nb_mesures_7j,
    s7.nb_mesures_good_7j,
    s7.nb_mesures_suspect_7j,
    ROUND((100.0 * s7.nb_mesures_good_7j / NULLIF(s7.nb_mesures_7j, 0))::NUMERIC, 1) AS pct_qualite_7j,
    -- Statut global du point
    CASE
        WHEN GREATEST(ld.derniere_heure_debit, lp.derniere_heure_pression, li.derniere_heure_index) 
             > CURRENT_TIMESTAMP - INTERVAL '2 hours' THEN 'ACTIF'
        WHEN GREATEST(ld.derniere_heure_debit, lp.derniere_heure_pression, li.derniere_heure_index) 
             > CURRENT_TIMESTAMP - INTERVAL '24 hours' THEN 'RECENT'
        WHEN GREATEST(ld.derniere_heure_debit, lp.derniere_heure_pression, li.derniere_heure_index) 
             > CURRENT_TIMESTAMP - INTERVAL '7 days' THEN 'ANCIEN'
        ELSE 'INACTIF'
    END AS statut_point,
    -- Timestamp de derniere activite
    GREATEST(
        ld.derniere_heure_debit, 
        lp.derniere_heure_pression, 
        li.derniere_heure_index,
        lv.derniere_heure_volume
    ) AS derniere_activite,
    -- Tooltip complet pour la carte (texte simple sans emojis)
    CONCAT(
        'Point: ', dp.nom_point, E'\n',
        'Groupe: ', COALESCE(dp.groupe_mesure, 'N/A'), E'\n',
        CASE WHEN ld.derniere_valeur_debit IS NOT NULL 
             THEN CONCAT('Debit: ', ROUND(ld.derniere_valeur_debit::NUMERIC, 1), ' m3/h', E'\n')
             ELSE '' END,
        CASE WHEN lp.derniere_valeur_pression IS NOT NULL 
             THEN CONCAT('Pression: ', ROUND(lp.derniere_valeur_pression::NUMERIC, 2), ' bar', E'\n')
             ELSE '' END,
        CASE WHEN li.derniere_valeur_index IS NOT NULL 
             THEN CONCAT('Index: ', ROUND(li.derniere_valeur_index::NUMERIC, 0), ' m3', E'\n')
             ELSE '' END
    ) AS tooltip_carte,
    -- Metadonnees refresh
    CURRENT_TIMESTAMP AS date_refresh
FROM dwh.dim_point_mesure dp
LEFT JOIN dwh.dim_source_mesure ds ON dp.id_source_mesure = ds.id_source_mesure
LEFT JOIN last_debit      ld ON dp.id_point_mesure = ld.id_point_mesure
LEFT JOIN last_pression   lp ON dp.id_point_mesure = lp.id_point_mesure
LEFT JOIN last_index      li ON dp.id_point_mesure = li.id_point_mesure
LEFT JOIN last_volume     lv ON dp.id_point_mesure = lv.id_point_mesure
LEFT JOIN stats_7j        s7 ON dp.id_point_mesure = s7.id_point_mesure
LEFT JOIN canal_labels    cl ON dp.id_pmac = cl.id_pmac
LEFT JOIN groupes_points  gp ON dp.id_point_mesure = gp.id_point_mesure
WHERE dp.est_actif = TRUE
  AND dp.latitude IS NOT NULL
  AND dp.longitude IS NOT NULL
  AND dp.latitude BETWEEN -90 AND 90
  AND dp.longitude BETWEEN -180 AND 180;

-- Index pour refresh CONCURRENTLY (requiert un index unique)
CREATE UNIQUE INDEX idx_vw_carte_pk 
    ON dwh.vw_pbi_carte_points_enrichie(id_point_mesure);

CREATE INDEX idx_vw_carte_groupe 
    ON dwh.vw_pbi_carte_points_enrichie(groupe_mesure);

CREATE INDEX idx_vw_carte_type 
    ON dwh.vw_pbi_carte_points_enrichie(type_point);

CREATE INDEX idx_vw_carte_statut 
    ON dwh.vw_pbi_carte_points_enrichie(statut_point);

COMMENT ON MATERIALIZED VIEW dwh.vw_pbi_carte_points_enrichie IS 
    'Vue materialisee pour Dashboard Carte enrichie : dernieres mesures + stats 7j + tooltip. Refresh horaire recommande.';