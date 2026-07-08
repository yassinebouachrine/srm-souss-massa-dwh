# db/queries.py
from db.connection import execute_query, execute_insert, execute_many
from datetime import datetime
import json


# ════════════════════════════════════════════════════════════════
# Dimensions (lire depuis gold)
# ════════════════════════════════════════════════════════════════

def get_provinces():
    """Get all provinces from dimension table."""
    return execute_query(
        "SELECT id_province, code_province, nom_province FROM gold.dim_province ORDER BY id_province"
    )


def get_centres(id_province: int = None):
    """Get centres, optionally filtered by province."""
    if id_province:
        return execute_query(
            """SELECT id_centre, code_centre, nom_centre, type_centre 
               FROM gold.dim_centre 
               WHERE id_province = %s ORDER BY nom_centre""",
            (id_province,),
        )
    return execute_query(
        "SELECT id_centre, code_centre, nom_centre, type_centre FROM gold.dim_centre ORDER BY nom_centre"
    )


def get_types_indicateur():
    """Get all indicator types."""
    return execute_query(
        """SELECT id_type_indicateur, code_indicateur, libelle_indicateur, unite, categorie 
           FROM gold.dim_type_indicateur_dp 
           ORDER BY categorie, code_indicateur"""
    )


def get_types_reclamation():
    """Get all reclamation types."""
    return execute_query(
        """SELECT id_type_reclamation, code_type, libelle_reclamation, 
                  categorie_reclamation, est_comptage, est_duree
           FROM gold.dim_type_reclamation 
           ORDER BY categorie_reclamation, code_type"""
    )


# ════════════════════════════════════════════════════════════════
# Staging: Indicateurs DP
# ════════════════════════════════════════════════════════════════

def insert_staging_indicateurs(records: list):
    """Insert multiple indicator records into staging."""
    query = """
        INSERT INTO app_staging.staging_indicateurs_dp 
            (id_province, nom_province, id_centre, nom_centre, annee, mois, nom_mois,
             code_indicateur, libelle_indicateur, unite, categorie,
             valeur_mensuelle, valeur_recapitulatif, statut, soumis_par, date_soumission, lot_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_province, id_centre, annee, mois, code_indicateur, lot_id) DO UPDATE
        SET valeur_mensuelle = EXCLUDED.valeur_mensuelle,
            valeur_recapitulatif = EXCLUDED.valeur_recapitulatif,
            date_modification = CURRENT_TIMESTAMP
    """
    execute_many(query, records)


def get_staging_indicateurs(id_province: int = None, statut: str = None, 
                             lot_id: str = None, annee: int = None, mois: int = None):
    """Get staging indicators with filters."""
    conditions = []
    params = []
    
    if id_province:
        conditions.append("id_province = %s")
        params.append(id_province)
    if statut:
        conditions.append("statut = %s")
        params.append(statut)
    if lot_id:
        conditions.append("lot_id = %s")
        params.append(lot_id)
    if annee:
        conditions.append("annee = %s")
        params.append(annee)
    if mois:
        conditions.append("mois = %s")
        params.append(mois)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    return execute_query(
        f"""
        SELECT s.*, 
               u1.nom_complet AS soumis_par_nom,
               u2.nom_complet AS valide_dp_par_nom,
               u3.nom_complet AS valide_reg_par_nom
        FROM app_staging.staging_indicateurs_dp s
        LEFT JOIN app_auth.utilisateurs u1 ON s.soumis_par = u1.id_utilisateur
        LEFT JOIN app_auth.utilisateurs u2 ON s.valide_par_dp = u2.id_utilisateur
        LEFT JOIN app_auth.utilisateurs u3 ON s.valide_par_regional = u3.id_utilisateur
        {where}
        ORDER BY s.date_creation DESC
        """,
        tuple(params) if params else None,
    )


def get_staging_lots(id_province: int = None, statut: str = None, data_type: str = "indicateurs"):
    """Get distinct lots with summary info."""
    table = "app_staging.staging_indicateurs_dp" if data_type == "indicateurs" else "app_staging.staging_reclamations_dp"
    
    conditions = []
    params = []
    if id_province:
        conditions.append("id_province = %s")
        params.append(id_province)
    if statut:
        conditions.append("statut = %s")
        params.append(statut)
    
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    return execute_query(
        f"""
        SELECT lot_id, id_province, nom_province, annee, mois, statut,
               COUNT(*) as nb_enregistrements,
               MIN(date_creation) as date_creation,
               MAX(date_modification) as date_modification
        FROM {table}
        {where}
        GROUP BY lot_id, id_province, nom_province, annee, mois, statut
        ORDER BY date_creation DESC
        """,
        tuple(params) if params else None,
    )


def update_staging_status(table: str, lot_id: str, new_status: str, 
                           user_id: int, comment: str = None, level: str = "dp"):
    """Update status of a batch of records."""
    if table == "indicateurs":
        tbl = "app_staging.staging_indicateurs_dp"
    else:
        tbl = "app_staging.staging_reclamations_dp"
    
    if level == "dp":
        execute_insert(
            f"""
            UPDATE {tbl}
            SET statut = %s, valide_par_dp = %s, date_validation_dp = CURRENT_TIMESTAMP,
                commentaire_dp = %s, date_modification = CURRENT_TIMESTAMP
            WHERE lot_id = %s
            """,
            (new_status, user_id, comment, lot_id),
        )
    elif level == "regional":
        execute_insert(
            f"""
            UPDATE {tbl}
            SET statut = %s, valide_par_regional = %s, date_validation_reg = CURRENT_TIMESTAMP,
                commentaire_regional = %s, date_modification = CURRENT_TIMESTAMP
            WHERE lot_id = %s
            """,
            (new_status, user_id, comment, lot_id),
        )


def submit_lot(table: str, lot_id: str, user_id: int):
    """Submit a draft lot for validation."""
    if table == "indicateurs":
        tbl = "app_staging.staging_indicateurs_dp"
    else:
        tbl = "app_staging.staging_reclamations_dp"
    
    execute_insert(
        f"""
        UPDATE {tbl}
        SET statut = 'soumis', soumis_par = %s, date_soumission = CURRENT_TIMESTAMP,
            date_modification = CURRENT_TIMESTAMP
        WHERE lot_id = %s AND statut = 'brouillon'
        """,
        (user_id, lot_id),
    )


# ════════════════════════════════════════════════════════════════
# Staging: Réclamations DP
# ════════════════════════════════════════════════════════════════

def insert_staging_reclamations(records: list):
    """Insert multiple reclamation records into staging."""
    query = """
        INSERT INTO app_staging.staging_reclamations_dp 
            (id_province, nom_province, id_centre, nom_centre, annee, mois,
             code_type, libelle_reclamation, categorie_reclamation,
             nombre_reclamations, temps_moyen_coupure_h, delai_moyen_traitement_j, valeur_brute,
             statut, soumis_par, date_soumission, lot_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_province, id_centre, annee, mois, code_type, lot_id) DO UPDATE
        SET nombre_reclamations = EXCLUDED.nombre_reclamations,
            temps_moyen_coupure_h = EXCLUDED.temps_moyen_coupure_h,
            delai_moyen_traitement_j = EXCLUDED.delai_moyen_traitement_j,
            valeur_brute = EXCLUDED.valeur_brute,
            date_modification = CURRENT_TIMESTAMP
    """
    execute_many(query, records)


def get_staging_reclamations(id_province: int = None, statut: str = None, 
                              lot_id: str = None, annee: int = None, mois: int = None):
    """Get staging reclamations with filters."""
    conditions = []
    params = []
    
    if id_province:
        conditions.append("id_province = %s")
        params.append(id_province)
    if statut:
        conditions.append("statut = %s")
        params.append(statut)
    if lot_id:
        conditions.append("lot_id = %s")
        params.append(lot_id)
    if annee:
        conditions.append("annee = %s")
        params.append(annee)
    if mois:
        conditions.append("mois = %s")
        params.append(mois)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    return execute_query(
        f"""
        SELECT s.*, 
               u1.nom_complet AS soumis_par_nom,
               u2.nom_complet AS valide_dp_par_nom,
               u3.nom_complet AS valide_reg_par_nom
        FROM app_staging.staging_reclamations_dp s
        LEFT JOIN app_auth.utilisateurs u1 ON s.soumis_par = u1.id_utilisateur
        LEFT JOIN app_auth.utilisateurs u2 ON s.valide_par_dp = u2.id_utilisateur
        LEFT JOIN app_auth.utilisateurs u3 ON s.valide_par_regional = u3.id_utilisateur
        {where}
        ORDER BY s.date_creation DESC
        """,
        tuple(params) if params else None,
    )


# ════════════════════════════════════════════════════════════════
# Transfer validated data to Gold
# ════════════════════════════════════════════════════════════════

def transfer_validated_indicateurs_to_gold(lot_id: str):
    """Transfer validated staging indicators to the gold fact table."""
    execute_insert(
        """
        INSERT INTO gold.fait_indicateurs_performance_dp
            (id_temps, id_province, id_centre, id_type_indicateur, 
             valeur_mensuelle, valeur_recapitulatif, fichier_source, onglet_source, date_chargement)
        SELECT 
            dt.id_temps,
            s.id_province,
            s.id_centre,
            ti.id_type_indicateur,
            s.valeur_mensuelle,
            s.valeur_recapitulatif,
            'STREAMLIT_SAISIE',
            s.lot_id,
            CURRENT_TIMESTAMP
        FROM app_staging.staging_indicateurs_dp s
        JOIN gold.dim_temps dt ON dt.annee = s.annee AND dt.mois = s.mois
        JOIN gold.dim_type_indicateur_dp ti ON ti.code_indicateur = s.code_indicateur
        WHERE s.lot_id = %s AND s.statut = 'valide_regional'
        ON CONFLICT DO NOTHING
        """,
        (lot_id,),
    )


def transfer_validated_reclamations_to_gold(lot_id: str):
    """Transfer validated staging reclamations to the gold fact table."""
    execute_insert(
        """
        INSERT INTO gold.fait_reclamations_dp
            (id_temps, id_province, id_centre, id_type_reclamation,
             nombre_reclamations, temps_moyen_coupure_h, delai_moyen_traitement_j, 
             valeur_brute, date_chargement)
        SELECT 
            dt.id_temps,
            s.id_province,
            s.id_centre,
            tr.id_type_reclamation,
            s.nombre_reclamations,
            s.temps_moyen_coupure_h,
            s.delai_moyen_traitement_j,
            s.valeur_brute,
            CURRENT_TIMESTAMP
        FROM app_staging.staging_reclamations_dp s
        JOIN gold.dim_temps dt ON dt.annee = s.annee AND dt.mois = s.mois
        JOIN gold.dim_type_reclamation tr ON tr.code_type = s.code_type
        WHERE s.lot_id = %s AND s.statut = 'valide_regional'
        ON CONFLICT DO NOTHING
        """,
        (lot_id,),
    )


# ════════════════════════════════════════════════════════════════
# Dashboard stats
# ════════════════════════════════════════════════════════════════

def get_dashboard_stats(id_province: int = None):
    """Get dashboard statistics."""
    prov_filter = "WHERE id_province = %s" if id_province else ""
    params = (id_province,) if id_province else None
    
    # Indicateurs stats
    indic_stats = execute_query(
        f"""
        SELECT statut, COUNT(*) as count 
        FROM app_staging.staging_indicateurs_dp 
        {prov_filter}
        GROUP BY statut
        """,
        params,
    )
    
    # Reclamations stats
    reclam_stats = execute_query(
        f"""
        SELECT statut, COUNT(*) as count 
        FROM app_staging.staging_reclamations_dp 
        {prov_filter}
        GROUP BY statut
        """,
        params,
    )
    
    return {
        "indicateurs": {row["statut"]: row["count"] for row in (indic_stats or [])},
        "reclamations": {row["statut"]: row["count"] for row in (reclam_stats or [])},
    }


def get_audit_logs(user_id: int = None, limit: int = 50):
    """Get audit logs."""
    if user_id:
        return execute_query(
            """
            SELECT al.*, u.nom_complet, u.username
            FROM app_auth.audit_logs al
            JOIN app_auth.utilisateurs u ON al.id_utilisateur = u.id_utilisateur
            WHERE al.id_utilisateur = %s
            ORDER BY al.date_action DESC LIMIT %s
            """,
            (user_id, limit),
        )
    return execute_query(
        """
        SELECT al.*, u.nom_complet, u.username
        FROM app_auth.audit_logs al
        JOIN app_auth.utilisateurs u ON al.id_utilisateur = u.id_utilisateur
        ORDER BY al.date_action DESC LIMIT %s
        """,
        (limit,),
    )