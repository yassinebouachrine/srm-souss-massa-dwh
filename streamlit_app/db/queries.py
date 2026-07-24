# streamlit_app/db/queries.py
"""Requêtes SQL vers la base de données app_staging + app_auth."""
from db.connection import execute_query, execute_insert, execute_many


# ════════════════════════════════════════════════════════════════
# RÉFÉRENTIELS (depuis app_staging.ref_*)
# ════════════════════════════════════════════════════════════════

def get_provinces():
    """Récupère toutes les provinces."""
    return execute_query(
        "SELECT id_province, code_province, nom_province FROM app_staging.ref_province ORDER BY id_province"
    )


def get_centres(id_province=None):
    """Récupère les centres, filtrables par province."""
    if id_province:
        return execute_query(
            """SELECT id_centre, code_centre, nom_centre, type_centre
               FROM app_staging.ref_centre
               WHERE id_province = %s
               ORDER BY nom_centre""",
            (id_province,),
        )
    return execute_query(
        "SELECT id_centre, code_centre, nom_centre, type_centre FROM app_staging.ref_centre ORDER BY nom_centre"
    )


def get_types_indicateur():
    """Récupère les types d'indicateurs actifs."""
    return execute_query(
        """SELECT id_type_indicateur, code_indicateur, libelle_indicateur, unite, categorie
           FROM app_staging.ref_type_indicateur
           WHERE est_actif = TRUE
           ORDER BY ordre_affichage, code_indicateur"""
    )


def get_types_reclamation():
    """Récupère les types de réclamations actifs."""
    return execute_query(
        """SELECT id_type_reclamation, code_type, libelle_reclamation,
                  categorie_reclamation, est_comptage, est_duree
           FROM app_staging.ref_type_reclamation
           WHERE est_actif = TRUE
           ORDER BY ordre_affichage, code_type"""
    )


# ════════════════════════════════════════════════════════════════
# STAGING INDICATEURS
# ════════════════════════════════════════════════════════════════

def insert_staging_indicateurs(records):
    """Insère des indicateurs en staging."""
    query = """
        INSERT INTO app_staging.staging_indicateurs_dp
            (id_province, nom_province, id_centre, nom_centre,
             annee, mois, nom_mois, code_indicateur, libelle_indicateur,
             unite, categorie, valeur_indicateur,
             statut, soumis_par, date_soumission, lot_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id_province, id_centre, annee, mois, code_indicateur, lot_id) DO UPDATE
        SET valeur_indicateur = EXCLUDED.valeur_indicateur,
            date_modification = CURRENT_TIMESTAMP
    """
    execute_many(query, records)


def get_staging_indicateurs(id_province=None, statut=None, lot_id=None, annee=None, mois=None):
    """Récupère les indicateurs de staging avec filtres."""
    conditions = []
    params = []
    if id_province:
        conditions.append("s.id_province = %s")
        params.append(id_province)
    if statut:
        conditions.append("s.statut = %s")
        params.append(statut)
    if lot_id:
        conditions.append("s.lot_id = %s")
        params.append(lot_id)
    if annee:
        conditions.append("s.annee = %s")
        params.append(annee)
    if mois:
        conditions.append("s.mois = %s")
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


# ════════════════════════════════════════════════════════════════
# STAGING RÉCLAMATIONS
# ════════════════════════════════════════════════════════════════

def insert_staging_reclamations(records):
    """Insère des réclamations en staging."""
    query = """
        INSERT INTO app_staging.staging_reclamations_dp
            (id_province, nom_province, id_centre, nom_centre,
             annee, mois, code_type, libelle_reclamation, categorie_reclamation,
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


def get_staging_reclamations(id_province=None, statut=None, lot_id=None, annee=None, mois=None):
    """Récupère les réclamations de staging avec filtres."""
    conditions = []
    params = []
    if id_province:
        conditions.append("s.id_province = %s")
        params.append(id_province)
    if statut:
        conditions.append("s.statut = %s")
        params.append(statut)
    if lot_id:
        conditions.append("s.lot_id = %s")
        params.append(lot_id)
    if annee:
        conditions.append("s.annee = %s")
        params.append(annee)
    if mois:
        conditions.append("s.mois = %s")
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
# LOTS (GROUPEMENTS)
# ════════════════════════════════════════════════════════════════

def get_staging_lots(id_province=None, statut=None, data_type="indicateurs"):
    """Récupère les lots groupés."""
    table = ("app_staging.staging_indicateurs_dp" if data_type == "indicateurs"
             else "app_staging.staging_reclamations_dp")
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


def get_draft_lots(id_province=None, data_type="indicateurs"):
    """Récupère uniquement les lots en brouillon."""
    return get_staging_lots(id_province=id_province, statut="brouillon", data_type=data_type)


def get_rejected_lots(id_province=None, data_type="indicateurs"):
    """Récupère les lots rejetés (par DP ou régional)."""
    table = ("app_staging.staging_indicateurs_dp" if data_type == "indicateurs"
             else "app_staging.staging_reclamations_dp")
    conditions = ["statut IN ('rejete_dp', 'rejete_regional')"]
    params = []
    if id_province:
        conditions.append("id_province = %s")
        params.append(id_province)

    where = "WHERE " + " AND ".join(conditions)

    return execute_query(
        f"""
        SELECT lot_id, id_province, nom_province, annee, mois, statut,
               COUNT(*) as nb_enregistrements,
               MIN(date_creation) as date_creation,
               MAX(date_modification) as date_modification
        FROM {table}
        {where}
        GROUP BY lot_id, id_province, nom_province, annee, mois, statut
        ORDER BY date_modification DESC
        """,
        tuple(params) if params else None,
    )


# ════════════════════════════════════════════════════════════════
# WORKFLOW (submit, validation, rejet)
# ════════════════════════════════════════════════════════════════

def submit_lot(table, lot_id, user_id):
    """Soumet un lot brouillon ou rejeté."""
    tbl = ("app_staging.staging_indicateurs_dp" if table == "indicateurs"
           else "app_staging.staging_reclamations_dp")
    execute_insert(
        f"""
        UPDATE {tbl}
        SET statut = 'soumis',
            soumis_par = %s,
            date_soumission = CURRENT_TIMESTAMP,
            date_modification = CURRENT_TIMESTAMP
        WHERE lot_id = %s AND statut IN ('brouillon', 'rejete_dp', 'rejete_regional')
        """,
        (user_id, lot_id),
    )


def update_staging_status(table, lot_id, new_status, user_id, comment=None, level="dp"):
    """Met à jour le statut d'un lot (validation ou rejet)."""
    tbl = ("app_staging.staging_indicateurs_dp" if table == "indicateurs"
           else "app_staging.staging_reclamations_dp")
    if level == "dp":
        execute_insert(
            f"""
            UPDATE {tbl}
            SET statut = %s,
                valide_par_dp = %s,
                date_validation_dp = CURRENT_TIMESTAMP,
                commentaire_dp = %s,
                date_modification = CURRENT_TIMESTAMP
            WHERE lot_id = %s
            """,
            (new_status, user_id, comment, lot_id),
        )
    elif level == "regional":
        execute_insert(
            f"""
            UPDATE {tbl}
            SET statut = %s,
                valide_par_regional = %s,
                date_validation_reg = CURRENT_TIMESTAMP,
                commentaire_regional = %s,
                date_modification = CURRENT_TIMESTAMP
            WHERE lot_id = %s
            """,
            (new_status, user_id, comment, lot_id),
        )


def update_staging_record(table, id_staging, field_updates: dict):
    """Met à jour un enregistrement individuel."""
    tbl = ("app_staging.staging_indicateurs_dp" if table == "indicateurs"
           else "app_staging.staging_reclamations_dp")
    set_clauses = []
    params = []
    for field, value in field_updates.items():
        set_clauses.append(f"{field} = %s")
        params.append(value)
    set_clauses.append("date_modification = CURRENT_TIMESTAMP")
    params.append(id_staging)

    execute_insert(
        f"UPDATE {tbl} SET {', '.join(set_clauses)} WHERE id_staging = %s",
        tuple(params),
    )


def reset_lot_for_correction(table, lot_id):
    """Remet un lot rejeté en brouillon pour correction."""
    tbl = ("app_staging.staging_indicateurs_dp" if table == "indicateurs"
           else "app_staging.staging_reclamations_dp")
    execute_insert(
        f"""
        UPDATE {tbl}
        SET statut = 'brouillon',
            valide_par_dp = NULL,
            date_validation_dp = NULL,
            commentaire_dp = NULL,
            valide_par_regional = NULL,
            date_validation_reg = NULL,
            commentaire_regional = NULL,
            date_modification = CURRENT_TIMESTAMP
        WHERE lot_id = %s AND statut IN ('rejete_dp', 'rejete_regional')
        """,
        (lot_id,),
    )


def delete_lot(table, lot_id):
    """Supprime définitivement un lot en brouillon."""
    tbl = ("app_staging.staging_indicateurs_dp" if table == "indicateurs"
           else "app_staging.staging_reclamations_dp")
    execute_insert(
        f"DELETE FROM {tbl} WHERE lot_id = %s AND statut = 'brouillon'",
        (lot_id,),
    )


# ════════════════════════════════════════════════════════════════
# STATISTIQUES DASHBOARD
# ════════════════════════════════════════════════════════════════

def get_dashboard_stats(id_province=None):
    """Statistiques pour le tableau de bord."""
    prov_filter = "WHERE id_province = %s" if id_province else ""
    params = (id_province,) if id_province else None

    indic_stats = execute_query(
        f"""SELECT statut, COUNT(*) as count
            FROM app_staging.staging_indicateurs_dp
            {prov_filter}
            GROUP BY statut""",
        params,
    )
    reclam_stats = execute_query(
        f"""SELECT statut, COUNT(*) as count
            FROM app_staging.staging_reclamations_dp
            {prov_filter}
            GROUP BY statut""",
        params,
    )
    return {
        "indicateurs": {row["statut"]: row["count"] for row in (indic_stats or [])},
        "reclamations": {row["statut"]: row["count"] for row in (reclam_stats or [])},
    }


# ════════════════════════════════════════════════════════════════
# AUDIT LOGS
# ════════════════════════════════════════════════════════════════

def get_audit_logs(user_id=None, id_province=None, annee=None, mois=None, limit=500):
    """
    Récupère les logs d'audit avec filtres avancés.
    
    Args:
        user_id: Filtrer par utilisateur spécifique
        id_province: Filtrer par province (via l'utilisateur)
        annee: Filtrer par année
        mois: Filtrer par mois (1-12)
        limit: Nombre max de résultats
    """
    conditions = []
    params = []

    if user_id:
        conditions.append("al.id_utilisateur = %s")
        params.append(user_id)

    if id_province is not None:
        conditions.append("u.id_province = %s")
        params.append(id_province)

    if annee:
        conditions.append("EXTRACT(YEAR FROM al.date_action) = %s")
        params.append(annee)

    if mois:
        conditions.append("EXTRACT(MONTH FROM al.date_action) = %s")
        params.append(mois)

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(limit)

    query = f"""
        SELECT al.*,
               u.nom_complet,
               u.username,
               u.role,
               u.code_province,
               u.id_province
        FROM app_auth.audit_logs al
        JOIN app_auth.utilisateurs u ON al.id_utilisateur = u.id_utilisateur
        {where_clause}
        ORDER BY al.date_action DESC
        LIMIT %s
    """

    return execute_query(query, tuple(params))


def get_audit_available_years():
    """Récupère les années disponibles dans les logs d'audit."""
    result = execute_query(
        """
        SELECT DISTINCT EXTRACT(YEAR FROM date_action)::int AS annee
        FROM app_auth.audit_logs
        ORDER BY annee DESC
        """
    )
    return [r["annee"] for r in (result or [])]

def get_audit_available_users():
    """
    Récupère TOUS les utilisateurs de la base (actifs et inactifs).
    Utilisé pour peupler le filtre de recherche par compte.
    """
    result = execute_query(
        """
        SELECT
            id_utilisateur,
            username,
            nom_complet,
            role,
            code_province,
            est_actif
        FROM app_auth.utilisateurs
        ORDER BY 
            CASE role
                WHEN 'super_admin' THEN 1
                WHEN 'admin_regional' THEN 2
                WHEN 'admin_dp' THEN 3
                WHEN 'agent_dp' THEN 4
                ELSE 5
            END,
            code_province NULLS FIRST,
            nom_complet
        """
    )
    return result or []


# ════════════════════════════════════════════════════════════════
# HISTORIQUE DES CORRECTIONS
# ════════════════════════════════════════════════════════════════

def log_correction(lot_id, data_type, id_staging, code_element, libelle_element,
                   champ_modifie, ancienne_valeur, nouvelle_valeur,
                   motif_rejet, corrige_par, role_correcteur):
    """Enregistre une correction dans l'historique."""
    execute_insert(
        """
        INSERT INTO app_staging.historique_corrections
            (lot_id, data_type, id_staging, code_element, libelle_element,
             champ_modifie, ancienne_valeur, nouvelle_valeur,
             motif_rejet, corrige_par, role_correcteur)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (lot_id, data_type, id_staging, code_element, libelle_element,
         champ_modifie, str(ancienne_valeur), str(nouvelle_valeur),
         motif_rejet, corrige_par, role_correcteur),
    )


def get_lot_corrections(lot_id):
    """Récupère l'historique des corrections d'un lot."""
    return execute_query(
        """
        SELECT h.*, u.nom_complet AS corrige_par_nom
        FROM app_staging.historique_corrections h
        LEFT JOIN app_auth.utilisateurs u ON h.corrige_par = u.id_utilisateur
        WHERE h.lot_id = %s
        ORDER BY h.date_correction DESC
        """,
        (lot_id,),
    )


def update_staging_record_with_history(table, id_staging, field_updates: dict,
                                        lot_id, code_element, libelle_element,
                                        motif_rejet, user_id, role):
    """
    Met à jour un enregistrement ET enregistre l'historique des changements.
    Compare les anciennes et nouvelles valeurs, et log uniquement ce qui a changé.
    """
    tbl = ("app_staging.staging_indicateurs_dp" if table == "indicateurs"
           else "app_staging.staging_reclamations_dp")

    # 1. Récupérer les valeurs actuelles
    current = execute_query(
        f"SELECT * FROM {tbl} WHERE id_staging = %s",
        (id_staging,),
        fetch="one"
    )

    if not current:
        return

    # 2. Comparer et logger les changements
    for field, new_value in field_updates.items():
        old_value = current.get(field)

        # Convertir pour comparaison (éviter les faux positifs)
        try:
            if old_value is not None and new_value is not None:
                if abs(float(old_value) - float(new_value)) < 0.001:
                    continue  # Pas de changement significatif
        except (ValueError, TypeError):
            if str(old_value) == str(new_value):
                continue

        # Enregistrer la modification
        log_correction(
            lot_id=lot_id,
            data_type=table,
            id_staging=id_staging,
            code_element=code_element,
            libelle_element=libelle_element,
            champ_modifie=field,
            ancienne_valeur=old_value,
            nouvelle_valeur=new_value,
            motif_rejet=motif_rejet,
            corrige_par=user_id,
            role_correcteur=role,
        )

    # 3. Effectuer la mise à jour
    set_clauses = []
    params = []
    for field, value in field_updates.items():
        set_clauses.append(f"{field} = %s")
        params.append(value)
    set_clauses.append("date_modification = CURRENT_TIMESTAMP")
    params.append(id_staging)

    execute_insert(
        f"UPDATE {tbl} SET {', '.join(set_clauses)} WHERE id_staging = %s",
        tuple(params),
    )


def get_dashboard_stats_filtered(id_province=None, annee=None, mois=None,
                                  role_view=None):
    """
    Statistiques du dashboard avec filtres année/mois/province.
    
    Args:
        role_view: 'agent_dp', 'admin_dp', 'admin_regional', 'super_admin'
                   - admin_regional : voit UNIQUEMENT les statuts >= valide_dp
                   - autres : voient tous les statuts
    """
    conditions_i = []
    params_i = []

    if id_province:
        conditions_i.append("id_province = %s")
        params_i.append(id_province)
    if annee:
        conditions_i.append("annee = %s")
        params_i.append(annee)
    if mois:
        conditions_i.append("mois = %s")
        params_i.append(mois)

    # ✅ Admin régional voit uniquement les données validées par admin DP
    if role_view == "admin_regional":
        conditions_i.append("statut IN ('valide_dp', 'valide_regional', 'rejete_regional')")

    where_i = "WHERE " + " AND ".join(conditions_i) if conditions_i else ""

    indic_stats = execute_query(
        f"""SELECT statut, COUNT(*) as count
            FROM app_staging.staging_indicateurs_dp
            {where_i}
            GROUP BY statut""",
        tuple(params_i) if params_i else None,
    )
    reclam_stats = execute_query(
        f"""SELECT statut, COUNT(*) as count
            FROM app_staging.staging_reclamations_dp
            {where_i}
            GROUP BY statut""",
        tuple(params_i) if params_i else None,
    )

    return {
        "indicateurs": {row["statut"]: row["count"] for row in (indic_stats or [])},
        "reclamations": {row["statut"]: row["count"] for row in (reclam_stats or [])},
    }


def get_province_full_stats(annee=None, mois=None, role_view=None):
    """
    Retourne pour chaque province les statistiques complètes par statut.
    Combine indicateurs + réclamations pour avoir le vrai total.
    
    Args:
        annee, mois : filtres période
        role_view : si 'admin_regional', filtre uniquement les statuts >= valide_dp
    """
    conditions = []
    params = []

    if annee:
        conditions.append("annee = %s")
        params.append(annee)
    if mois:
        conditions.append("mois = %s")
        params.append(mois)

    if role_view == "admin_regional":
        conditions.append("statut IN ('valide_dp', 'valide_regional', 'rejete_regional')")

    where_clause = "AND " + " AND ".join(conditions) if conditions else ""

    result = execute_query(
        f"""
        SELECT
            p.id_province,
            p.nom_province,
            COALESCE(SUM(CASE WHEN combined.statut = 'brouillon' THEN combined.cnt END), 0) AS brouillon,
            COALESCE(SUM(CASE WHEN combined.statut = 'soumis' THEN combined.cnt END), 0) AS soumis,
            COALESCE(SUM(CASE WHEN combined.statut = 'valide_dp' THEN combined.cnt END), 0) AS valide_dp,
            COALESCE(SUM(CASE WHEN combined.statut = 'rejete_dp' THEN combined.cnt END), 0) AS rejete_dp,
            COALESCE(SUM(CASE WHEN combined.statut = 'valide_regional' THEN combined.cnt END), 0) AS valide_regional,
            COALESCE(SUM(CASE WHEN combined.statut = 'rejete_regional' THEN combined.cnt END), 0) AS rejete_regional,
            COALESCE(SUM(combined.cnt), 0) AS total
        FROM app_staging.ref_province p
        LEFT JOIN (
            SELECT id_province, statut, COUNT(*) AS cnt
            FROM app_staging.staging_indicateurs_dp
            WHERE 1=1 {where_clause}
            GROUP BY id_province, statut

            UNION ALL

            SELECT id_province, statut, COUNT(*) AS cnt
            FROM app_staging.staging_reclamations_dp
            WHERE 1=1 {where_clause}
            GROUP BY id_province, statut
        ) combined ON p.id_province = combined.id_province
        GROUP BY p.id_province, p.nom_province
        ORDER BY p.id_province
        """,
        tuple(params + params) if params else None,
    )
    return result or []



def get_activity_timeline(annee=None, mois=None, id_province=None, role_view=None):
    """
    Récupère l'activité mensuelle par province.
    Applique les mêmes filtres que le dashboard.
    """
    conditions = []
    params = []

    if annee:
        conditions.append("annee = %s")
        params.append(annee)
    if mois:
        conditions.append("mois = %s")
        params.append(mois)
    if id_province:
        conditions.append("id_province = %s")
        params.append(id_province)

    if role_view == "admin_regional":
        conditions.append("statut IN ('valide_dp', 'valide_regional', 'rejete_regional')")

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    result = execute_query(
        f"""
        SELECT
            nom_province,
            id_province,
            annee,
            mois,
            SUM(nb_indic) AS nb_indicateurs,
            SUM(nb_reclam) AS nb_reclamations,
            SUM(nb_indic + nb_reclam) AS nb_total
        FROM (
            SELECT
                nom_province, id_province, annee, mois,
                COUNT(*) AS nb_indic,
                0 AS nb_reclam
            FROM app_staging.staging_indicateurs_dp
            {where_clause}
            GROUP BY nom_province, id_province, annee, mois

            UNION ALL

            SELECT
                nom_province, id_province, annee, mois,
                0 AS nb_indic,
                COUNT(*) AS nb_reclam
            FROM app_staging.staging_reclamations_dp
            {where_clause}
            GROUP BY nom_province, id_province, annee, mois
        ) combined
        GROUP BY nom_province, id_province, annee, mois
        ORDER BY annee, mois, nom_province
        """,
        tuple(params + params) if params else None,
    )
    return result or []


def get_dp_activity_summary(annee=None, mois=None, id_province=None, role_view=None):
    """
    Vue globale de l'activité par DP avec application des filtres complets.
    """
    conditions = []
    params = []

    if annee:
        conditions.append("annee = %s")
        params.append(annee)
    if mois:
        conditions.append("mois = %s")
        params.append(mois)

    if role_view == "admin_regional":
        conditions.append("statut IN ('valide_dp', 'valide_regional', 'rejete_regional')")

    inner_where = "AND " + " AND ".join(conditions) if conditions else ""

    # Filtre province au niveau outer
    outer_where = ""
    outer_params = []
    if id_province:
        outer_where = "WHERE p.id_province = %s"
        outer_params = [id_province]

    result = execute_query(
        f"""
        SELECT
            p.id_province,
            p.nom_province,
            p.code_province,
            COALESCE(indic.nb_indicateurs, 0) AS nb_indicateurs,
            COALESCE(reclam.nb_reclamations, 0) AS nb_reclamations,
            COALESCE(indic.nb_indicateurs, 0) + COALESCE(reclam.nb_reclamations, 0) AS nb_total,
            GREATEST(
                COALESCE(indic.derniere_saisie, '1900-01-01'::timestamp),
                COALESCE(reclam.derniere_saisie, '1900-01-01'::timestamp)
            ) AS derniere_saisie,
            COALESCE(indic.nb_valides, 0) + COALESCE(reclam.nb_valides, 0) AS nb_valides,
            COALESCE(indic.nb_soumis, 0) + COALESCE(reclam.nb_soumis, 0) AS nb_soumis
        FROM app_staging.ref_province p
        LEFT JOIN (
            SELECT
                id_province,
                COUNT(*) AS nb_indicateurs,
                MAX(date_creation) AS derniere_saisie,
                COUNT(*) FILTER (WHERE statut = 'valide_regional') AS nb_valides,
                COUNT(*) FILTER (WHERE statut IN ('soumis', 'valide_dp')) AS nb_soumis
            FROM app_staging.staging_indicateurs_dp
            WHERE 1=1 {inner_where}
            GROUP BY id_province
        ) indic ON p.id_province = indic.id_province
        LEFT JOIN (
            SELECT
                id_province,
                COUNT(*) AS nb_reclamations,
                MAX(date_creation) AS derniere_saisie,
                COUNT(*) FILTER (WHERE statut = 'valide_regional') AS nb_valides,
                COUNT(*) FILTER (WHERE statut IN ('soumis', 'valide_dp')) AS nb_soumis
            FROM app_staging.staging_reclamations_dp
            WHERE 1=1 {inner_where}
            GROUP BY id_province
        ) reclam ON p.id_province = reclam.id_province
        {outer_where}
        ORDER BY p.id_province
        """,
        tuple(params + params + outer_params) if (params or outer_params) else None,
    )
    return result or []


def get_available_years_dashboard():
    """Récupère les années disponibles dans les données saisies."""
    result = execute_query(
        """
        SELECT DISTINCT annee FROM (
            SELECT annee FROM app_staging.staging_indicateurs_dp
            UNION
            SELECT annee FROM app_staging.staging_reclamations_dp
        ) years
        ORDER BY annee DESC
        """
    )
    return [r["annee"] for r in (result or [])]
