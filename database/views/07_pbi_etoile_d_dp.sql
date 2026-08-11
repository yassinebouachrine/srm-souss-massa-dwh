-- ═══════════════════════════════════════════════════════════════
-- VUES PBI — INDICATEURS DP & RÉCLAMATIONS (Étoile D)
-- Pour les dashboards des indicateurs de performance DP
-- ═══════════════════════════════════════════════════════════════


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_INDICATEURS_DP : Indicateurs de performance
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_indicateurs_dp AS
SELECT
    f.id_fait,
    -- Temps
    t.date_complete   AS date_mois,
    t.annee,
    t.mois,
    t.nom_mois,
    t.annee::TEXT || '-' || LPAD(t.mois::TEXT, 2, '0') AS annee_mois,
    -- DP
    dp.code_dp,
    dp.nom_dp,
    dp.region,
    -- Centre
    dc.code_centre,
    dc.nom_centre,
    dc.type_centre,
    (dc.id_centre = 0) AS est_agregation_dp,
    -- Indicateur
    ti.code_indicateur,
    ti.libelle_indicateur,
    ti.unite,
    ti.categorie,
    -- Valeur
    f.valeur,
    -- Source
    f.source_saisie,
    f.fichier_source,
    f.date_chargement
FROM dwh.fait_indicateurs_performance_dp f
JOIN dwh.dim_temps               t  ON f.id_temps = t.id_temps
JOIN dwh.dim_dp                  dp ON f.id_dp = dp.id_dp
JOIN dwh.dim_centre              dc ON f.id_centre = dc.id_centre
JOIN dwh.dim_type_indicateur_dp  ti ON f.id_type_indicateur = ti.id_type_indicateur;

COMMENT ON VIEW dwh.vw_pbi_indicateurs_dp IS 
    'Indicateurs de performance DP pour Power BI';


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_RECLAMATIONS_DP : Réclamations
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_reclamations_dp AS
SELECT
    f.id_fait,
    -- Temps
    t.date_complete   AS date_mois,
    t.annee,
    t.mois,
    t.nom_mois,
    t.annee::TEXT || '-' || LPAD(t.mois::TEXT, 2, '0') AS annee_mois,
    -- DP & Centre
    dp.code_dp,
    dp.nom_dp,
    dc.code_centre,
    dc.nom_centre,
    (dc.id_centre = 0) AS est_agregation_dp,
    -- Type réclamation
    tr.code                  AS code_reclamation,
    tr.libelle               AS libelle_reclamation,
    tr.categorie             AS categorie_reclamation,
    tr.est_personnalisee,
    -- Mesures
    f.nb_reclamations,
    f.temps_moyen_coupure,
    f.delai_moyen_traitement,
    f.valeur_brute,
    -- Source
    f.source_saisie,
    f.fichier_source
FROM dwh.fait_reclamation f
JOIN dwh.dim_temps            t  ON f.id_temps = t.id_temps
JOIN dwh.dim_dp               dp ON f.id_dp = dp.id_dp
JOIN dwh.dim_centre           dc ON f.id_centre = dc.id_centre
JOIN dwh.dim_type_reclamation tr ON f.id_type = tr.id_type;

COMMENT ON VIEW dwh.vw_pbi_reclamations_dp IS 
    'Réclamations pour Power BI (Excel + Streamlit)';