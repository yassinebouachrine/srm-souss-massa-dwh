-- ═══════════════════════════════════════════════════════════════
-- VUES PBI — GSTCOM (Étoile A)
-- Pour les pages : Evol Anomalies, Âge Compteurs, Conso Client
-- ═══════════════════════════════════════════════════════════════


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_ANOMALIES_ETAGE : Anomalies compteurs par étage
-- Utilisé par : Evol Anomalies / Étage (6 KPIs)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_anomalies_etage AS
SELECT
    e.code_etage,
    e.nom_etage,
    t.date_complete AS date_mois,
    t.annee,
    t.mois,
    t.annee::TEXT || '-' || LPAD(t.mois::TEXT, 2, '0') AS annee_mois,
    ta.code_anomalie,
    ta.libelle_anomalie,
    ta.categorie                     AS categorie_anomalie,
    ta.gravite,
    ta.est_bloquant,
    SUM(f.nb_anomalies * f.pct_repartition_etage)::INT     AS nb_anomalies_ponderees,
    COUNT(DISTINCT f.id_client)                            AS nb_clients_distincts,
    -- Métriques par type (pour cartes KPI)
    SUM(CASE WHEN ta.code_anomalie = 'A' THEN 1 ELSE 0 END) AS nb_clients_absents,
    SUM(CASE WHEN ta.code_anomalie = 'K' THEN 1 ELSE 0 END) AS nb_compteurs_bloques,
    SUM(CASE WHEN ta.code_anomalie = 'I' THEN 1 ELSE 0 END) AS nb_compteurs_inaccessibles,
    SUM(CASE WHEN ta.code_anomalie = 'M' THEN 1 ELSE 0 END) AS nb_compteurs_changes,
    SUM(CASE WHEN ta.code_anomalie = 'E' THEN 1 ELSE 0 END) AS nb_compteurs_envers,
    SUM(CASE WHEN ta.code_anomalie = 'P' THEN 1 ELSE 0 END) AS nb_compteurs_panne
FROM dwh.fait_anomalie_compteur f
JOIN dwh.dim_temps         t  ON f.id_temps = t.id_temps
JOIN dwh.dim_etage         e  ON f.id_etage = e.id_etage
JOIN dwh.dim_type_anomalie ta ON f.id_type_anomalie = ta.id_type_anomalie
WHERE e.est_actif = TRUE
GROUP BY e.code_etage, e.nom_etage, t.date_complete, t.annee, t.mois,
         ta.code_anomalie, ta.libelle_anomalie, ta.categorie, ta.gravite, ta.est_bloquant;

COMMENT ON VIEW dwh.vw_pbi_anomalies_etage IS 
    'Anomalies compteurs par étage — page Evol Anomalies / Étage';


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_AGE_COMPTEURS_ETAGE : Âge moyen des compteurs
-- Utilisé par : Âge Compteurs / Étage
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_age_compteurs_etage AS
SELECT
    e.code_etage,
    e.nom_etage,
    t.date_complete AS date_mois,
    t.annee,
    t.mois,
    t.annee::TEXT || '-' || LPAD(t.mois::TEXT, 2, '0') AS annee_mois,
    t.nom_mois || ' ' || t.annee::TEXT AS mois_annee_label,
    COUNT(DISTINCT c.id_client) AS nb_compteurs,
    -- Âge moyen pondéré par répartition étage
    ROUND(
        (SUM(c.age_compteur_annees * f.pct_repartition_etage) 
         / NULLIF(SUM(f.pct_repartition_etage), 0))::NUMERIC, 2
    ) AS age_compteur_moyen,
    MIN(c.age_compteur_annees) AS age_min,
    MAX(c.age_compteur_annees) AS age_max
FROM dwh.fait_consommation_client f
JOIN dwh.dim_client c ON f.id_client = c.id_client
JOIN dwh.dim_temps  t ON f.id_temps  = t.id_temps
JOIN dwh.dim_etage  e ON f.id_etage  = e.id_etage
WHERE e.est_actif = TRUE
  AND c.age_compteur_annees IS NOT NULL
GROUP BY e.code_etage, e.nom_etage, t.date_complete, t.annee, t.mois, t.nom_mois;

COMMENT ON VIEW dwh.vw_pbi_age_compteurs_etage IS 
    'Âge moyen compteurs par étage — page Âge Compteurs / Étage';


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_CONSOMMATION_ETAGE : Consommation client pondérée par étage
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_consommation_etage AS
SELECT
    e.code_etage,
    e.nom_etage,
    t.date_complete AS date_mois,
    t.annee,
    t.mois,
    t.annee::TEXT || '-' || LPAD(t.mois::TEXT, 2, '0') AS annee_mois,
    -- Agrégats pondérés
    COUNT(DISTINCT f.id_client) AS nb_clients,
    COUNT(DISTINCT f.id_client) FILTER (WHERE c.est_gros_conso) AS nb_gros_conso,
    ROUND(SUM(f.conso_reelle    * f.pct_repartition_etage)::NUMERIC, 2) AS conso_reelle_totale,
    ROUND(SUM(f.conso_facturee  * f.pct_repartition_etage)::NUMERIC, 2) AS conso_facturee_totale,
    ROUND(SUM(f.conso_rapportee * f.pct_repartition_etage)::NUMERIC, 2) AS conso_rapportee_totale,
    ROUND(AVG(f.nb_jours_releve)::NUMERIC, 1) AS nb_jours_releve_moyen,
    ROUND(AVG(f.conso_facturee * f.pct_repartition_etage)::NUMERIC, 2) AS conso_moyenne_client
FROM dwh.fait_consommation_client f
JOIN dwh.dim_client c ON f.id_client = c.id_client
JOIN dwh.dim_temps  t ON f.id_temps  = t.id_temps
JOIN dwh.dim_etage  e ON f.id_etage  = e.id_etage
WHERE e.est_actif = TRUE
GROUP BY e.code_etage, e.nom_etage, t.date_complete, t.annee, t.mois;

COMMENT ON VIEW dwh.vw_pbi_consommation_etage IS 
    'Consommation client agrégée par étage';


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_CLIENTS_DETAIL : Détail clients pour drill-down
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_clients_detail AS
SELECT
    c.id_client,
    c.police,
    c.numero_compteur,
    c.nom_client,
    c.adresse,
    c.latitude,
    c.longitude,
    c.categorie,
    c.tournee,
    c.age_compteur_annees,
    c.date_installation_compteur,
    c.est_gros_conso,
    c.statut_client,
    -- Loc/Sec
    c.loc,
    c.sec,
    ls.code_loc_sec,
    -- Étage principal (celui avec le pct max)
    (SELECT e.nom_etage
     FROM dwh.bridge_loc_sec_etage b
     JOIN dwh.dim_etage e ON b.id_etage = e.id_etage
     WHERE b.id_loc_sec = c.id_loc_sec
     ORDER BY b.pct_effectif DESC
     LIMIT 1
    ) AS etage_principal
FROM dwh.dim_client c
LEFT JOIN dwh.dim_loc_sec ls ON c.id_loc_sec = ls.id_loc_sec
WHERE c.id_client > 0;

COMMENT ON VIEW dwh.vw_pbi_clients_detail IS 
    'Détail clients GSTCOM pour drill-down PBI';