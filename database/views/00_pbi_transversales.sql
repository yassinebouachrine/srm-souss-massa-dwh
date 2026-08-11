-- ═══════════════════════════════════════════════════════════════
-- VUES PBI — DIMENSIONS TRANSVERSALES
-- Optimisées pour Power BI (colonnes préformatées, hiérarchies)
-- ═══════════════════════════════════════════════════════════════


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_DIM_TEMPS : Calendrier Power BI
-- Hiérarchies : Annee → Trimestre → Mois → Jour
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_dim_temps AS
SELECT
    id_temps,
    date_complete,
    jour,
    mois,
    nom_mois,
    trimestre,
    'T' || trimestre AS trimestre_label,
    annee,
    -- Concaténations utiles pour PBI
    annee::TEXT || '-' || LPAD(mois::TEXT, 2, '0')            AS annee_mois,
    nom_mois || ' ' || annee::TEXT                             AS mois_annee_label,
    LPAD(mois::TEXT, 2, '0') || ' - ' || nom_mois              AS mois_ordonne,
    -- Attributs métier
    jour_semaine,
    est_ferie,
    est_weekend,
    -- Flags relatifs
    (date_complete = CURRENT_DATE) AS est_aujourdhui,
    (annee = EXTRACT(YEAR FROM CURRENT_DATE)) AS est_annee_courante,
    (annee = EXTRACT(YEAR FROM CURRENT_DATE) 
     AND mois = EXTRACT(MONTH FROM CURRENT_DATE)) AS est_mois_courant
FROM dwh.dim_temps;

COMMENT ON VIEW dwh.vw_pbi_dim_temps IS 
    'Dimension Temps pour Power BI avec hiérarchies et flags métier';


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_DIM_ETAGE : Étages hydrauliques
-- Inclut linéaire, cote, géoloc pour cartes
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_dim_etage AS
SELECT
    id_etage,
    code_etage,
    nom_etage,
    type_etage,
    lineaire_km,
    cote_altitude,
    capacite_reservoir_m3,
    secteur_principal,
    dp_responsable,
    nom_region,
    nom_province,
    nom_centre,
    latitude,
    longitude,
    est_actif,
    -- Flags PBI
    (type_etage = 'Agrégation') AS est_agregat,
    (type_etage = 'Réservoir')  AS est_reservoir_etage
FROM dwh.dim_etage
WHERE est_actif = TRUE;

COMMENT ON VIEW dwh.vw_pbi_dim_etage IS 
    'Dimension Étage hydraulique pour Power BI';


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_DIM_SECTEUR : Secteurs hydrauliques
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_dim_secteur AS
SELECT
    id_secteur,
    code_secteur,
    nom_secteur,
    nom_secteur_hydraulique,
    lineaire_m,
    ROUND((lineaire_m / 1000.0)::NUMERIC, 3) AS lineaire_km,
    nom_region,
    nom_province,
    nom_centre,
    dp,
    est_actif
FROM dwh.dim_secteur
WHERE est_actif = TRUE;

COMMENT ON VIEW dwh.vw_pbi_dim_secteur IS 
    'Dimension Secteur hydraulique pour Power BI';


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_DIM_POINT_MESURE : Points de mesure enrichis
-- Inclut source, canaux, flags, label métier
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_dim_point_mesure AS
SELECT
    dp.id_point_mesure,
    dp.id_pmac,
    dp.nom_point,
    dp.station_pcwin,
    dp.groupe_mesure,
    -- Source
    ds.code_source,
    ds.libelle_source,
    ds.type_systeme,
    -- Géoloc
    dp.latitude,
    dp.longitude,
    dp.cote_altitude,
    dp.capacite_reservoir_m3,
    -- Flags capacités
    dp.est_pression,
    dp.est_debit,
    dp.est_reservoir,
    dp.est_amont,
    dp.est_aval,
    dp.est_modulateur,
    -- Attributs techniques
    dp.canal_affichage,
    dp.code_voie,
    -- Statut
    dp.est_actif,
    -- Type dérivé pour PBI (utile pour filtrage/icônes)
    CASE
        WHEN dp.est_modulateur   THEN 'Modulateur'
        WHEN dp.est_reservoir    THEN 'Réservoir'
        WHEN dp.est_pression     THEN 'Point Pression'
        WHEN dp.est_debit        THEN 'Point Débit'
        ELSE 'Autre'
    END AS type_point,
    -- Icône ArcGIS (pour la carte)
    CASE
        WHEN dp.est_modulateur   THEN 'triangle'
        WHEN dp.est_reservoir    THEN 'square'
        ELSE 'circle'
    END AS forme_icone
FROM dwh.dim_point_mesure dp
LEFT JOIN dwh.dim_source_mesure ds ON dp.id_source_mesure = ds.id_source_mesure
WHERE dp.est_actif = TRUE;

COMMENT ON VIEW dwh.vw_pbi_dim_point_mesure IS 
    'Dimension Point de mesure unifié PMAC+PCWIN pour Power BI';