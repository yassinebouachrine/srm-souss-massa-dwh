-- ═══════════════════════════════════════════════════════════════
-- VUES PBI — MESURES TEMPS RÉEL (Étoile B)
-- Pour les pages : Courbes DEBIT, Courbes PRESSION, Courbes INDEX
-- ═══════════════════════════════════════════════════════════════


-- ─────────────────────────────────────────────────────────────
-- VW_PBI_MESURES_TEMPS_REEL : Toutes les mesures pour courbes
-- Colonnes optimisées pour PBI avec jointures pré-faites
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW dwh.vw_pbi_mesures_temps_reel AS
SELECT
    -- ─── Clés ───
    f.id_fait,
    f.id_temps,
    f.id_point_mesure,
    f.id_source_mesure,
    -- ─── Timestamp (utile pour axes X) ───
    f.heure,
    DATE(f.heure)                    AS date_mesure,
    EXTRACT(HOUR FROM f.heure)::INT  AS heure_du_jour,
    -- ─── Attributs point de mesure ───
    dp.id_pmac,
    dp.nom_point,
    dp.groupe_mesure,
    dp.est_reservoir,
    dp.est_modulateur,
    -- ─── Source ───
    ds.code_source,
    ds.libelle_source,
    -- ─── Mesures brutes ───
    f.voie,
    f.canal,
    f.unite,
    f.pression_bar,
    f.pression_amont_bar,
    f.pression_aval_bar,
    f.debit_m3_h,
    f.volume_15min,
    f.index_compteur,
    -- ─── Valeur unifiée pour PBI (pratique pour graphiques dynamiques) ───
    COALESCE(
        f.debit_m3_h, 
        f.pression_bar, 
        f.pression_amont_bar, 
        f.pression_aval_bar,
        f.index_compteur, 
        f.volume_15min
    ) AS valeur_mesure,
    -- ─── Qualité ───
    f.qualite_donnees,
    (f.qualite_donnees = 'GOOD')    AS est_qualite_ok,
    (f.qualite_donnees = 'SUSPECT') AS est_qualite_suspect,
    -- ─── Delta calcul pour tendances ───
    LAG(f.debit_m3_h) OVER (
        PARTITION BY f.id_point_mesure, f.canal 
        ORDER BY f.heure
    ) AS debit_precedent
FROM dwh.fait_mesure_temps_reel f
JOIN dwh.dim_point_mesure  dp ON f.id_point_mesure = dp.id_point_mesure
JOIN dwh.dim_source_mesure ds ON f.id_source_mesure = ds.id_source_mesure
WHERE dp.est_actif = TRUE;

COMMENT ON VIEW dwh.vw_pbi_mesures_temps_reel IS 
    'Mesures capteurs pour les courbes DEBIT/PRESSION/INDEX Power BI';