-- ═══════════════════════════════════════════════════════════════
-- VUE DE CONTRÔLE : Calcul dynamique du statut des lots
-- ═══════════════════════════════════════════════════════════════

CREATE OR REPLACE VIEW app_staging.v_lot_statut_calcule AS
SELECT 
    l.id_lot,
    l.statut_agrege AS statut_enregistre,
    COUNT(d.id_donnee) AS nb_lignes,
    COUNT(d.id_donnee) FILTER (WHERE d.statut = 'brouillon') AS nb_brouillon,
    COUNT(d.id_donnee) FILTER (WHERE d.statut = 'soumis') AS nb_soumis,
    COUNT(d.id_donnee) FILTER (WHERE d.statut = 'valide_dp') AS nb_valide_dp,
    COUNT(d.id_donnee) FILTER (WHERE d.statut = 'rejete_dp') AS nb_rejete_dp,
    COUNT(d.id_donnee) FILTER (WHERE d.statut = 'valide_regional') AS nb_valide_reg,
    COUNT(d.id_donnee) FILTER (WHERE d.statut = 'rejete_regional') AS nb_rejete_reg,
    CASE 
        WHEN COUNT(d.id_donnee) = 0 THEN 'vide'
        WHEN COUNT(d.id_donnee) FILTER (WHERE d.statut = 'brouillon') = COUNT(d.id_donnee) THEN 'brouillon'
        WHEN COUNT(d.id_donnee) FILTER (WHERE d.statut = 'soumis') = COUNT(d.id_donnee) THEN 'soumis'
        WHEN COUNT(d.id_donnee) FILTER (WHERE d.statut = 'valide_regional') = COUNT(d.id_donnee) THEN 'valide_regional'
        WHEN COUNT(d.id_donnee) FILTER (WHERE d.statut = 'valide_dp') = COUNT(d.id_donnee) THEN 'valide_dp'
        WHEN COUNT(d.id_donnee) FILTER (WHERE d.statut = 'rejete_dp') > 0 THEN 'partiellement_rejete_dp'
        WHEN COUNT(d.id_donnee) FILTER (WHERE d.statut = 'rejete_regional') > 0 THEN 'partiellement_rejete_regional'
        ELSE 'en_cours_traitement'
    END AS statut_calcule_exact
FROM app_staging.lot_saisie l
LEFT JOIN app_staging.donnee_saisie d ON l.id_lot = d.id_lot
GROUP BY l.id_lot, l.statut_agrege;


-- ═══════════════════════════════════════════════════════════════
-- VUES COMPATIBILITÉ ETL (Pont entre 3NF et l'ETL Bronze)
-- ═══════════════════════════════════════════════════════════════

-- ─── Suppression des vues existantes pour re-création ───
DROP VIEW IF EXISTS app_staging.staging_indicateurs_dp CASCADE;
DROP VIEW IF EXISTS app_staging.staging_reclamations_dp CASCADE;


-- ─── 1. Vue Indicateurs ───
CREATE VIEW app_staging.staging_indicateurs_dp AS
SELECT 
    d.id_donnee AS id_staging,
    l.id_lot::text AS lot_id,
    p.id_province,
    p.nom_province,
    c.id_centre,
    c.nom_centre,
    per.annee,
    per.mois,
    CASE per.mois
        WHEN 1 THEN 'Janvier' WHEN 2 THEN 'Février' WHEN 3 THEN 'Mars'
        WHEN 4 THEN 'Avril' WHEN 5 THEN 'Mai' WHEN 6 THEN 'Juin'
        WHEN 7 THEN 'Juillet' WHEN 8 THEN 'Août' WHEN 9 THEN 'Septembre'
        WHEN 10 THEN 'Octobre' WHEN 11 THEN 'Novembre' WHEN 12 THEN 'Décembre'
    END AS nom_mois,
    ti.code_indicateur,
    ti.libelle_indicateur,
    ti.unite,
    ti.categorie,
    si.valeur_indicateur,
    d.statut,
    u_creator.nom_complet AS soumis_par,
    l.date_soumission,
    u_dp.nom_complet AS valide_par_dp,
    v_dp.date_validation AS date_validation_dp,
    u_reg.nom_complet AS valide_par_regional,
    v_reg.date_validation AS date_validation_reg,
    l.date_creation,
    d.date_modification
FROM app_staging.donnee_saisie d
JOIN app_staging.saisie_indicateur si ON d.id_donnee = si.id_donnee
JOIN app_staging.ref_type_indicateur ti ON si.id_type_indicateur = ti.id_type_indicateur
JOIN app_staging.lot_saisie l ON d.id_lot = l.id_lot
JOIN app_staging.ref_centre c ON l.id_centre = c.id_centre
JOIN app_staging.ref_province p ON c.id_province = p.id_province
JOIN app_staging.ref_periode per ON l.id_periode = per.id_periode
JOIN app_auth.utilisateurs u_creator ON l.cree_par = u_creator.id_utilisateur
LEFT JOIN app_staging.validation v_dp ON v_dp.id_validation = (
    SELECT id_validation FROM app_staging.validation 
    WHERE id_donnee = d.id_donnee AND niveau = 'dp' 
    ORDER BY date_validation DESC LIMIT 1
)
LEFT JOIN app_auth.utilisateurs u_dp ON v_dp.valide_par = u_dp.id_utilisateur
LEFT JOIN app_staging.validation v_reg ON v_reg.id_validation = (
    SELECT id_validation FROM app_staging.validation 
    WHERE id_donnee = d.id_donnee AND niveau = 'regional' 
    ORDER BY date_validation DESC LIMIT 1
)
LEFT JOIN app_auth.utilisateurs u_reg ON v_reg.valide_par = u_reg.id_utilisateur;


-- ─── 2. Vue Réclamations (uniquement les standards + AUTRES) ───
CREATE VIEW app_staging.staging_reclamations_dp AS
SELECT 
    d.id_donnee AS id_staging,
    l.id_lot::text AS lot_id,
    p.id_province,
    p.nom_province,
    c.id_centre,
    c.nom_centre,
    per.annee,
    per.mois,
    tr.code_type,
    tr.libelle_reclamation,
    tr.categorie_reclamation,
    sr.nombre_reclamations,
    sr.temps_moyen_coupure_h,
    sr.delai_moyen_traitement_j,
    sr.valeur_brute,
    sr.commentaire_autre,
    d.statut,
    u_creator.nom_complet AS soumis_par,
    l.date_soumission,
    u_dp.nom_complet AS valide_par_dp,
    v_dp.date_validation AS date_validation_dp,
    u_reg.nom_complet AS valide_par_regional,
    v_reg.date_validation AS date_validation_reg,
    l.date_creation,
    d.date_modification
FROM app_staging.donnee_saisie d
JOIN app_staging.saisie_reclamation sr ON d.id_donnee = sr.id_donnee
JOIN app_staging.ref_type_reclamation tr ON sr.id_type_reclamation = tr.id_type_reclamation
JOIN app_staging.lot_saisie l ON d.id_lot = l.id_lot
JOIN app_staging.ref_centre c ON l.id_centre = c.id_centre
JOIN app_staging.ref_province p ON c.id_province = p.id_province
JOIN app_staging.ref_periode per ON l.id_periode = per.id_periode
JOIN app_auth.utilisateurs u_creator ON l.cree_par = u_creator.id_utilisateur
LEFT JOIN app_staging.validation v_dp ON v_dp.id_validation = (
    SELECT id_validation FROM app_staging.validation 
    WHERE id_donnee = d.id_donnee AND niveau = 'dp' 
    ORDER BY date_validation DESC LIMIT 1
)
LEFT JOIN app_auth.utilisateurs u_dp ON v_dp.valide_par = u_dp.id_utilisateur
LEFT JOIN app_staging.validation v_reg ON v_reg.id_validation = (
    SELECT id_validation FROM app_staging.validation 
    WHERE id_donnee = d.id_donnee AND niveau = 'regional' 
    ORDER BY date_validation DESC LIMIT 1
)
LEFT JOIN app_auth.utilisateurs u_reg ON v_reg.valide_par = u_reg.id_utilisateur;