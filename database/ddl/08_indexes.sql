-- ============================================================
-- Fichier : 08_indexes.sql
-- Projet  : SRM Souss-Massa DWH
-- Date    : Juillet 2026
-- ============================================================

-- TODO: Ajouter les instructions SQL ici
-- ============================================================
-- Fichier : 08_indexes.sql
-- Objectif: Indexes pour optimiser les performances
-- ============================================================

-- ────────────────────────────────────────────
-- INDEXES STAGING
-- ────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_stg_ind_statut 
    ON staging.indicateurs_dp(statut, est_traite);
CREATE INDEX IF NOT EXISTS idx_stg_ind_date 
    ON staging.indicateurs_dp(annee, mois);
CREATE INDEX IF NOT EXISTS idx_stg_ind_province 
    ON staging.indicateurs_dp(id_province);

CREATE INDEX IF NOT EXISTS idx_stg_rec_statut 
    ON staging.reclamations_dp(statut, est_traite);
CREATE INDEX IF NOT EXISTS idx_stg_rec_date 
    ON staging.reclamations_dp(annee, mois);

CREATE INDEX IF NOT EXISTS idx_stg_rend_statut 
    ON staging.rendements_etage(statut, est_traite);


-- ────────────────────────────────────────────
-- INDEXES BRONZE
-- ────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_br_ind_date 
    ON bronze.streamlit_indicateurs_dp(annee, mois);
CREATE INDEX IF NOT EXISTS idx_br_ind_ingestion 
    ON bronze.streamlit_indicateurs_dp(date_ingestion);

CREATE INDEX IF NOT EXISTS idx_br_inx_capteur 
    ON bronze.capteurs_inx(code_capteur);
CREATE INDEX IF NOT EXISTS idx_br_inx_datetime 
    ON bronze.capteurs_inx(datetime_source);
CREATE INDEX IF NOT EXISTS idx_br_inx_date 
    ON bronze.capteurs_inx(date_mesure);

CREATE INDEX IF NOT EXISTS idx_br_pmac_capteur 
    ON bronze.capteurs_pmac(code_capteur);
CREATE INDEX IF NOT EXISTS idx_br_pmac_type 
    ON bronze.capteurs_pmac(type_mesure);
CREATE INDEX IF NOT EXISTS idx_br_pmac_datetime 
    ON bronze.capteurs_pmac(datetime_source);

CREATE INDEX IF NOT EXISTS idx_br_gstcom_police 
    ON bronze.clientele_gstcom(police);
CREATE INDEX IF NOT EXISTS idx_br_gstcom_loc_sec 
    ON bronze.clientele_gstcom(loc, sec);

CREATE INDEX IF NOT EXISTS idx_br_alarme_capteur 
    ON bronze.capteurs_alarmes(code_capteur, datetime_alarme);


-- ────────────────────────────────────────────
-- INDEXES SILVER
-- ────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_sv_ind_date 
    ON silver.indicateurs_dp_clean(annee, mois);
CREATE INDEX IF NOT EXISTS idx_sv_ind_province 
    ON silver.indicateurs_dp_clean(id_province);

CREATE INDEX IF NOT EXISTS idx_sv_capt_capteur 
    ON silver.capteurs_normalises(code_capteur);
CREATE INDEX IF NOT EXISTS idx_sv_capt_type 
    ON silver.capteurs_normalises(type_mesure);
CREATE INDEX IF NOT EXISTS idx_sv_capt_datetime 
    ON silver.capteurs_normalises(datetime_source);

CREATE INDEX IF NOT EXISTS idx_sv_client_police 
    ON silver.clientele_clean(num_police);


-- ────────────────────────────────────────────
-- INDEXES GOLD - DIMENSIONS
-- ────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_dim_temps_date 
    ON gold.dim_temps(date_complete);
CREATE INDEX IF NOT EXISTS idx_dim_temps_annee_mois 
    ON gold.dim_temps(annee, mois);

CREATE INDEX IF NOT EXISTS idx_dim_client_police 
    ON gold.dim_client(num_police);
CREATE INDEX IF NOT EXISTS idx_dim_client_localite 
    ON gold.dim_client(id_localite);

CREATE INDEX IF NOT EXISTS idx_dim_capteur_code 
    ON gold.dim_capteur(code_capteur);
CREATE INDEX IF NOT EXISTS idx_dim_capteur_type 
    ON gold.dim_capteur(type_capteur);
CREATE INDEX IF NOT EXISTS idx_dim_capteur_groupe 
    ON gold.dim_capteur(id_groupe_mesure);

CREATE INDEX IF NOT EXISTS idx_dim_canal_key 
    ON gold.dim_canal_mapping(key_canal);


-- ────────────────────────────────────────────
-- INDEXES GOLD - FAITS
-- ────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_fait_ind_temps 
    ON gold.fait_indicateurs_performance_dp(id_temps);
CREATE INDEX IF NOT EXISTS idx_fait_ind_province 
    ON gold.fait_indicateurs_performance_dp(id_province);
CREATE INDEX IF NOT EXISTS idx_fait_ind_type 
    ON gold.fait_indicateurs_performance_dp(id_type_indicateur);

CREATE INDEX IF NOT EXISTS idx_fait_rec_temps 
    ON gold.fait_reclamations_dp(id_temps);
CREATE INDEX IF NOT EXISTS idx_fait_rec_province 
    ON gold.fait_reclamations_dp(id_province);

CREATE INDEX IF NOT EXISTS idx_fait_rend_temps 
    ON gold.fait_rendement_etage(id_temps);
CREATE INDEX IF NOT EXISTS idx_fait_rend_etage 
    ON gold.fait_rendement_etage(id_etage);

CREATE INDEX IF NOT EXISTS idx_fait_cons_client 
    ON gold.fait_consommation_client(id_client);
CREATE INDEX IF NOT EXISTS idx_fait_cons_temps 
    ON gold.fait_consommation_client(id_temps);
CREATE INDEX IF NOT EXISTS idx_fait_cons_etage 
    ON gold.fait_consommation_client(id_etage);

CREATE INDEX IF NOT EXISTS idx_fait_mes_capteur 
    ON gold.fait_mesures_capteur(id_capteur);
CREATE INDEX IF NOT EXISTS idx_fait_mes_temps 
    ON gold.fait_mesures_capteur(id_temps);
CREATE INDEX IF NOT EXISTS idx_fait_mes_type 
    ON gold.fait_mesures_capteur(id_type_mesure);
CREATE INDEX IF NOT EXISTS idx_fait_mes_datetime 
    ON gold.fait_mesures_capteur(datetime_source);


-- ────────────────────────────────────────────
-- INDEXES AUDIT
-- ────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_audit_saisies_user 
    ON audit.log_saisies(utilisateur, date_action);
CREATE INDEX IF NOT EXISTS idx_audit_saisies_table 
    ON audit.log_saisies(table_cible, date_action);

CREATE INDEX IF NOT EXISTS idx_audit_etl_dag 
    ON audit.log_etl(dag_id, execution_date);
CREATE INDEX IF NOT EXISTS idx_audit_etl_statut 
    ON audit.log_etl(statut, execution_date);


-- ────────────────────────────────────────────
-- Verification
-- ────────────────────────────────────────────
SELECT 
    schemaname,
    COUNT(*) AS nb_indexes
FROM pg_indexes
WHERE schemaname IN ('staging', 'bronze', 'silver', 'gold', 'audit')
GROUP BY schemaname
ORDER BY schemaname;