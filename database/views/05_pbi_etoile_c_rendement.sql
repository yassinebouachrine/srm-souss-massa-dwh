-- ═══════════════════════════════════════════════════════════════
-- VUES PBI — RENDEMENTS PAR ÉTAGE (Étoile C)
-- Pour les pages : Vue Globale, Histo Evol, Volume Pertes, ILP, etc.
-- ═══════════════════════════════════════════════════════════════


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_RENDEMENT_ETAGE_MENSUEL : Vue principale rendements
-- Utilisé par : Vue Globale, KPI/Étage, Rendement 2026
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_rendement_etage_mensuel AS
SELECT
    -- ─── Clés ───
    f.id_fait,
    f.id_temps,
    f.id_etage,
    -- ─── Temps ───
    t.date_complete                    AS date_mois,
    t.annee,
    t.mois,
    t.nom_mois,
    t.annee::TEXT || '-' || LPAD(t.mois::TEXT, 2, '0') AS annee_mois,
    t.nom_mois || ' ' || t.annee::TEXT AS mois_annee_label,
    -- ─── Étage ───
    e.code_etage,
    e.nom_etage,
    e.type_etage,
    e.lineaire_km,
    e.cote_altitude,
    e.nom_province,
    e.latitude,
    e.longitude,
    -- ─── Volumes ───
    f.volume_amene,
    f.volume_facture,
    f.volume_pertes,
    f.volume_facture_ebo,
    f.volume_amene_ramsa,
    -- ─── Clients ───
    f.nb_clients,
    f.age_compteur_moyen,
    f.nb_jours_moyen_releve,
    -- ─── Rendements (en % pour PBI) ───
    ROUND((f.rendement * 100)::NUMERIC, 2)         AS rendement_pct,
    ROUND((f.rendement_off * 100)::NUMERIC, 2)     AS rendement_off_pct,
    ROUND((f.pseudo_rendement * 100)::NUMERIC, 2)  AS pseudo_rendement_pct,
    f.rendement,           -- Décimal pour calculs DAX
    f.rendement_off,
    f.pseudo_rendement,
    -- ─── ILP ───
    ROUND(f.ilp::NUMERIC, 3)                       AS ilp,
    -- ─── Métadonnées ───
    f.source_donnees,
    f.date_chargement,
    -- ─── Flags analytiques ───
    (f.rendement >= 0.80)                          AS est_rendement_bon,
    (f.rendement BETWEEN 0.60 AND 0.80)            AS est_rendement_moyen,
    (f.rendement < 0.60)                           AS est_rendement_faible,
    (f.volume_pertes IS NOT NULL AND f.volume_pertes > 0) AS a_des_pertes
FROM dwh.fait_rendement_etage f
JOIN dwh.dim_temps  t ON f.id_temps = t.id_temps
JOIN dwh.dim_etage  e ON f.id_etage = e.id_etage
WHERE e.est_actif = TRUE;

COMMENT ON VIEW dwh.vw_pbi_rendement_etage_mensuel IS 
    'Rendement mensuel par étage — Vue Globale, KPI/Étage, Rendement 2026';


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_RENDEMENT_EVOLUTION : Évolution historique
-- Utilisé par : Histo Evol Rendement / Étage
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_rendement_evolution AS
SELECT
    e.code_etage,
    e.nom_etage,
    e.lineaire_km,
    e.latitude,
    e.longitude,
    t.date_complete AS date_mois,
    t.annee,
    t.mois,
    t.annee::TEXT || '-' || LPAD(t.mois::TEXT, 2, '0') AS annee_mois,
    ROUND((f.rendement * 100)::NUMERIC, 2) AS rendement_pct,
    -- Rendement mois précédent (pour zone hausse/baisse)
    LAG(f.rendement) OVER (
        PARTITION BY e.code_etage ORDER BY t.date_complete
    ) AS rendement_mois_precedent,
    -- Variation
    ROUND(
        ((f.rendement - LAG(f.rendement) OVER (
            PARTITION BY e.code_etage ORDER BY t.date_complete
        )) * 100)::NUMERIC, 2
    ) AS variation_rendement_pct,
    -- Label hausse/baisse (pour coloration PBI)
    CASE 
        WHEN f.rendement > LAG(f.rendement) OVER (
            PARTITION BY e.code_etage ORDER BY t.date_complete
        ) THEN 'HAUSSE'
        WHEN f.rendement < LAG(f.rendement) OVER (
            PARTITION BY e.code_etage ORDER BY t.date_complete
        ) THEN 'BAISSE'
        ELSE 'STABLE'
    END AS tendance,
    f.volume_amene,
    f.volume_facture,
    f.volume_pertes,
    ROUND(f.ilp::NUMERIC, 3) AS ilp
FROM dwh.fait_rendement_etage f
JOIN dwh.dim_temps t ON f.id_temps = t.id_temps
JOIN dwh.dim_etage e ON f.id_etage = e.id_etage
WHERE e.est_actif = TRUE
  AND f.rendement IS NOT NULL;

COMMENT ON VIEW dwh.vw_pbi_rendement_evolution IS 
    'Évolution historique rendement avec tendances — page Histo Evol Rendement';


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_VOLUME_PERTES_ETAGE : Volumes de pertes
-- Utilisé par : Volume Pertes / Étage
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_volume_pertes_etage AS
SELECT
    e.code_etage,
    e.nom_etage,
    e.lineaire_km,
    t.date_complete AS date_mois,
    t.annee,
    t.mois,
    t.annee::TEXT || '-' || LPAD(t.mois::TEXT, 2, '0') AS annee_mois,
    f.volume_amene,
    f.volume_facture,
    f.volume_pertes,
    ROUND(f.ilp::NUMERIC, 3) AS ilp,
    -- % de pertes globales du mois
    ROUND(
        (100.0 * f.volume_pertes / NULLIF(
            SUM(f.volume_pertes) OVER (PARTITION BY t.date_complete), 0
        ))::NUMERIC, 2
    ) AS pct_pertes_du_mois
FROM dwh.fait_rendement_etage f
JOIN dwh.dim_temps t ON f.id_temps = t.id_temps
JOIN dwh.dim_etage e ON f.id_etage = e.id_etage
WHERE e.est_actif = TRUE
  AND f.volume_pertes IS NOT NULL
  AND f.volume_pertes > 0;

COMMENT ON VIEW dwh.vw_pbi_volume_pertes_etage IS 
    'Volumes de pertes par étage — page Volume Pertes / Étage';