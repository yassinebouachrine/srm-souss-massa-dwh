# db/queries.py
"""
Requêtes SQL normalisées vers la base de données (Schéma 3NF app_staging + app_auth).
Gère la validation par ligne, le rejet ciblé, le recalcul du statut du lot,
et l'historique détaillé des corrections.
"""

from db.connection import execute_query, execute_insert, execute_many
import logging

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# RÉFÉRENTIELS (depuis app_staging.ref_* & app_auth.ref_*)
# ════════════════════════════════════════════════════════════════

def get_provinces():
    """Récupère toutes les provinces."""
    return execute_query(
        "SELECT id_province, code_province, nom_province, est_siege FROM app_staging.ref_province ORDER BY id_province"
    )


def get_centres(id_province=None):
    """Récupère les centres, filtrables par province."""
    if id_province:
        return execute_query(
            """
            SELECT c.id_centre, c.code_centre, c.nom_centre, c.type_centre, c.id_province, p.nom_province
            FROM app_staging.ref_centre c
            JOIN app_staging.ref_province p ON c.id_province = p.id_province
            WHERE c.id_province = %s
            ORDER BY c.nom_centre
            """,
            (id_province,),
        )
    return execute_query(
        """
        SELECT c.id_centre, c.code_centre, c.nom_centre, c.type_centre, c.id_province, p.nom_province
        FROM app_staging.ref_centre c
        JOIN app_staging.ref_province p ON c.id_province = p.id_province
        ORDER BY p.id_province, c.nom_centre
        """
    )


def get_or_create_periode(annee: int, mois: int) -> int:
    """Récupère ou crée l'ID de la période (annee, mois)."""
    res = execute_query(
        "SELECT id_periode FROM app_staging.ref_periode WHERE annee = %s AND mois = %s",
        (annee, mois),
        fetch="one",
    )
    if res:
        return res["id_periode"]

    new_p = execute_insert(
        "INSERT INTO app_staging.ref_periode (annee, mois) VALUES (%s, %s) RETURNING id_periode",
        (annee, mois),
    )
    return new_p[0] if new_p else None


def get_types_indicateur():
    """Récupère les types d'indicateurs actifs."""
    return execute_query(
        """
        SELECT id_type_indicateur, code_indicateur, libelle_indicateur, unite, categorie
        FROM app_staging.ref_type_indicateur
        WHERE est_actif = TRUE
        ORDER BY ordre_affichage, code_indicateur
        """
    )


def get_types_reclamation():
    """Récupère les types de réclamations actifs."""
    return execute_query(
        """
        SELECT id_type_reclamation, code_type, libelle_reclamation,
               categorie_reclamation, est_comptage, est_duree
        FROM app_staging.ref_type_reclamation
        WHERE est_actif = TRUE
        ORDER BY ordre_affichage, code_type
        """
    )


def get_roles():
    """Récupère tous les rôles."""
    return execute_query("SELECT id_role, code_role, libelle_role FROM app_auth.ref_role ORDER BY id_role")


# ════════════════════════════════════════════════════════════════
# LOGIQUE DU STATUT AGRÉGÉ DU LOT (Option B)
# ════════════════════════════════════════════════════════════════

def recalculer_statut_lot(id_lot: int) -> str:
    counts = execute_query(
        """
        SELECT 
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE statut = 'brouillon') AS brouillon,
            COUNT(*) FILTER (WHERE statut = 'soumis') AS soumis,
            COUNT(*) FILTER (WHERE statut = 'valide_dp') AS valide_dp,
            COUNT(*) FILTER (WHERE statut = 'rejete_dp') AS rejete_dp,
            COUNT(*) FILTER (WHERE statut = 'valide_regional') AS valide_regional,
            COUNT(*) FILTER (WHERE statut = 'rejete_regional') AS rejete_regional,
            COUNT(*) FILTER (WHERE statut = 'modif_admin_dp') AS modif_admin_dp,
            COUNT(*) FILTER (WHERE statut = 'modif_agent_dp') AS modif_agent_dp
        FROM app_staging.donnee_saisie
        WHERE id_lot = %s
        """,
        (id_lot,),
        fetch="one",
    )

    if not counts or counts["total"] == 0:
        new_status = "brouillon"
    else:
        tot = counts["total"]

        # États homogènes
        if counts["brouillon"] == tot: new_status = "brouillon"
        elif counts["valide_regional"] == tot: new_status = "valide_regional"
        elif counts["valide_dp"] == tot: new_status = "valide_dp"
        elif counts["soumis"] == tot: new_status = "soumis"

        # NOUVEAUX : États "en modification"
        elif counts["modif_agent_dp"] > 0: new_status = "en_modification_agent"
        elif counts["modif_admin_dp"] > 0: new_status = "en_modification_admin_dp"

        # États mixtes existants
        elif counts["soumis"] > 0: new_status = "en_cours_validation_dp"
        elif counts["rejete_dp"] > 0: new_status = "partiellement_rejete_dp"
        elif counts["rejete_regional"] > 0: new_status = "partiellement_rejete_regional"
        elif counts["valide_dp"] > 0:
            new_status = "en_cours_validation_regional" if counts["valide_regional"] > 0 else "valide_dp"
        else:
            new_status = "en_cours_traitement"

    execute_insert(
        "UPDATE app_staging.lot_saisie SET statut_agrege = %s WHERE id_lot = %s",
        (new_status, id_lot),
    )
    return new_status

# ════════════════════════════════════════════════════════════════
# INSERTIONS (SAISIE INDICATEURS ET RÉCLAMATIONS)
# ════════════════════════════════════════════════════════════════

def create_or_get_lot(id_centre: int, id_periode: int, type_donnees: str, user_id: int, is_submit: bool = False) -> int:
    """Crée ou récupère l'enveloppe LotSaisie."""
    existing = execute_query(
        "SELECT id_lot FROM app_staging.lot_saisie WHERE id_centre = %s AND id_periode = %s AND type_donnees = %s",
        (id_centre, id_periode, type_donnees),
        fetch="one",
    )
    if existing:
        if is_submit:
            execute_insert(
                "UPDATE app_staging.lot_saisie SET date_soumission = CURRENT_TIMESTAMP WHERE id_lot = %s",
                (existing["id_lot"],),
            )
        return existing["id_lot"]

    date_soum = "CURRENT_TIMESTAMP" if is_submit else "NULL"
    query = f"""
        INSERT INTO app_staging.lot_saisie (id_centre, id_periode, type_donnees, cree_par, date_soumission)
        VALUES (%s, %s, %s, %s, {date_soum})
        RETURNING id_lot
    """
    res = execute_insert(query, (id_centre, id_periode, type_donnees, user_id))
    return res[0] if res else None


def insert_indicateurs_batch(id_centre: int, annee: int, mois: int, records: list, user_id: int, is_submit: bool = False):
    """
    Insère un lot d'indicateurs.
    Si le créateur est admin_dp et is_submit=True → auto-validation DP.
    """
    id_periode = get_or_create_periode(annee, mois)
    id_lot = create_or_get_lot(id_centre, id_periode, "indicateurs", user_id, is_submit)

    user_role = execute_query(
        """
        SELECT r.code_role FROM app_auth.utilisateurs u
        JOIN app_auth.ref_role r ON u.id_role = r.id_role
        WHERE u.id_utilisateur = %s
        """,
        (user_id,), fetch="one"
    )
    is_admin_dp = user_role and user_role["code_role"] in ("admin_dp", "super_admin")
    auto_valide_dp = is_submit and is_admin_dp

    if auto_valide_dp:
        statut_initial = "valide_dp"
    elif is_submit:
        statut_initial = "soumis"
    else:
        statut_initial = "brouillon"

    for r in records:
        existing = execute_query(
            """
            SELECT d.id_donnee 
            FROM app_staging.donnee_saisie d
            JOIN app_staging.saisie_indicateur i ON d.id_donnee = i.id_donnee
            WHERE d.id_lot = %s AND i.id_type_indicateur = %s
            """,
            (id_lot, r["id_type_indicateur"]),
            fetch="one",
        )

        if existing:
            id_donnee = existing["id_donnee"]
            execute_insert(
                "UPDATE app_staging.donnee_saisie SET statut = %s, date_modification = CURRENT_TIMESTAMP WHERE id_donnee = %s",
                (statut_initial, id_donnee),
            )
            execute_insert(
                "UPDATE app_staging.saisie_indicateur SET valeur_indicateur = %s WHERE id_donnee = %s",
                (r["valeur"], id_donnee),
            )
        else:
            res_d = execute_insert(
                "INSERT INTO app_staging.donnee_saisie (id_lot, type_donnee, statut) VALUES (%s, 'indicateur', %s) RETURNING id_donnee",
                (id_lot, statut_initial),
            )
            id_donnee = res_d[0]
            execute_insert(
                "INSERT INTO app_staging.saisie_indicateur (id_donnee, id_type_indicateur, valeur_indicateur) VALUES (%s, %s, %s)",
                (id_donnee, r["id_type_indicateur"], r["valeur"]),
            )

        if auto_valide_dp:
            execute_insert(
                """
                INSERT INTO app_staging.validation 
                    (id_donnee, niveau, decision, commentaire, valide_par)
                VALUES (%s, 'dp', 'valide', 'Auto-validation Admin DP', %s)
                """,
                (id_donnee, user_id),
            )

    recalculer_statut_lot(id_lot)
    return id_lot


def insert_reclamations_batch(id_centre: int, annee: int, mois: int, records_std: list, user_id: int, is_submit: bool = False):
    """
    Insère un lot de réclamations standards uniquement
    (y compris type AUTRES + commentaire_autre optionnel).
    """
    id_periode = get_or_create_periode(annee, mois)
    id_lot = create_or_get_lot(id_centre, id_periode, "reclamations", user_id, is_submit)

    user_role = execute_query(
        """
        SELECT r.code_role FROM app_auth.utilisateurs u
        JOIN app_auth.ref_role r ON u.id_role = r.id_role
        WHERE u.id_utilisateur = %s
        """,
        (user_id,), fetch="one"
    )
    is_admin_dp = user_role and user_role["code_role"] in ("admin_dp", "super_admin")
    auto_valide_dp = is_submit and is_admin_dp

    if auto_valide_dp:
        statut_initial = "valide_dp"
    elif is_submit:
        statut_initial = "soumis"
    else:
        statut_initial = "brouillon"

    for r in records_std:
        existing = execute_query(
            """
            SELECT d.id_donnee 
            FROM app_staging.donnee_saisie d
            JOIN app_staging.saisie_reclamation rec ON d.id_donnee = rec.id_donnee
            WHERE d.id_lot = %s AND rec.id_type_reclamation = %s
            """,
            (id_lot, r["id_type_reclamation"]),
            fetch="one",
        )

        commentaire_autre = r.get("commentaire_autre")  # None si pas AUTRES

        if existing:
            id_donnee = existing["id_donnee"]
            execute_insert(
                "UPDATE app_staging.donnee_saisie SET statut = %s, date_modification = CURRENT_TIMESTAMP WHERE id_donnee = %s",
                (statut_initial, id_donnee),
            )
            execute_insert(
                """
                UPDATE app_staging.saisie_reclamation 
                SET nombre_reclamations = %s,
                    temps_moyen_coupure_h = %s,
                    delai_moyen_traitement_j = %s,
                    valeur_brute = %s,
                    commentaire_autre = %s
                WHERE id_donnee = %s
                """,
                (r["nb"], r["temps_coupure"], r["delai_traitement"], r["valeur_brute"], commentaire_autre, id_donnee),
            )
        else:
            res_d = execute_insert(
                "INSERT INTO app_staging.donnee_saisie (id_lot, type_donnee, statut) VALUES (%s, 'reclamation', %s) RETURNING id_donnee",
                (id_lot, statut_initial),
            )
            id_donnee = res_d[0]
            execute_insert(
                """
                INSERT INTO app_staging.saisie_reclamation 
                    (id_donnee, id_type_reclamation, nombre_reclamations,
                     temps_moyen_coupure_h, delai_moyen_traitement_j, valeur_brute, commentaire_autre)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (id_donnee, r["id_type_reclamation"], r["nb"], r["temps_coupure"], r["delai_traitement"], r["valeur_brute"], commentaire_autre),
            )

        if auto_valide_dp:
            execute_insert(
                """
                INSERT INTO app_staging.validation 
                    (id_donnee, niveau, decision, commentaire, valide_par)
                VALUES (%s, 'dp', 'valide', 'Auto-validation Admin DP', %s)
                """,
                (id_donnee, user_id),
            )

    recalculer_statut_lot(id_lot)
    return id_lot

# ════════════════════════════════════════════════════════════════
# RÉCUPÉRATION DES LOTS ET DÉTAILS
# ════════════════════════════════════════════════════════════════

def get_staging_lots(id_province=None, statut=None, type_donnees="indicateurs", user_id=None):
    """
    Récupère la liste des lots selon filtres.
    Si le statut est 'brouillon' et user_id est fourni, restreint aux brouillons de cet utilisateur.
    """
    conditions = ["l.type_donnees = %s"]
    params = [type_donnees]

    if id_province:
        conditions.append("c.id_province = %s")
        params.append(id_province)

    if statut:
        conditions.append("l.statut_agrege = %s")
        params.append(statut)

    if statut == "brouillon" and user_id:
        conditions.append("l.cree_par = %s")
        params.append(user_id)

    where = "WHERE " + " AND ".join(conditions)

    return execute_query(
        f"""
        SELECT 
            l.id_lot, l.id_centre, c.nom_centre, c.id_province, p.nom_province, p.code_province,
            per.annee, per.mois, l.type_donnees, l.statut_agrege AS statut,
            l.cree_par, u.nom_complet AS cree_par_nom,
            l.date_creation, l.date_soumission,
            COUNT(d.id_donnee) AS nb_enregistrements
        FROM app_staging.lot_saisie l
        JOIN app_staging.ref_centre c ON l.id_centre = c.id_centre
        JOIN app_staging.ref_province p ON c.id_province = p.id_province
        JOIN app_staging.ref_periode per ON l.id_periode = per.id_periode
        JOIN app_auth.utilisateurs u ON l.cree_par = u.id_utilisateur
        LEFT JOIN app_staging.donnee_saisie d ON l.id_lot = d.id_lot
        {where}
        GROUP BY l.id_lot, c.nom_centre, c.id_province, p.nom_province, p.code_province,
                 per.annee, per.mois, u.nom_complet
        ORDER BY l.date_creation DESC
        """,
        tuple(params),
    )


def get_lot_details_indicateurs(id_lot: int):
    """Récupère toutes les lignes d'indicateurs d'un lot."""
    return execute_query(
        """
        SELECT 
            d.id_donnee, d.id_lot, d.statut, d.date_modification,
            ti.code_indicateur, ti.libelle_indicateur, ti.unite, ti.categorie,
            si.valeur_indicateur,
            v.decision AS derniere_decision, 
            v.commentaire AS dernier_commentaire,
            v.niveau AS niveau_decision
        FROM app_staging.donnee_saisie d
        JOIN app_staging.saisie_indicateur si ON d.id_donnee = si.id_donnee
        JOIN app_staging.ref_type_indicateur ti ON si.id_type_indicateur = ti.id_type_indicateur
        LEFT JOIN app_staging.validation v ON v.id_validation = (
            SELECT id_validation FROM app_staging.validation 
            WHERE id_donnee = d.id_donnee ORDER BY date_validation DESC LIMIT 1
        )
        WHERE d.id_lot = %s
        ORDER BY ti.ordre_affichage, ti.code_indicateur
        """,
        (id_lot,),
    )


def get_lot_details_reclamations(id_lot: int):
    """Récupère les réclamations d'un lot (standards + AUTRES avec commentaire)."""
    return execute_query(
        """
        SELECT 
            d.id_donnee, d.id_lot, d.statut, d.date_modification, d.type_donnee,
            tr.code_type, tr.libelle_reclamation, tr.categorie_reclamation,
            sr.nombre_reclamations, sr.temps_moyen_coupure_h, 
            sr.delai_moyen_traitement_j, sr.valeur_brute,
            sr.commentaire_autre,
            v.decision AS derniere_decision, 
            v.commentaire AS dernier_commentaire,
            v.niveau AS niveau_decision
        FROM app_staging.donnee_saisie d
        JOIN app_staging.saisie_reclamation sr ON d.id_donnee = sr.id_donnee
        JOIN app_staging.ref_type_reclamation tr ON sr.id_type_reclamation = tr.id_type_reclamation
        LEFT JOIN app_staging.validation v ON v.id_validation = (
            SELECT id_validation FROM app_staging.validation 
            WHERE id_donnee = d.id_donnee ORDER BY date_validation DESC LIMIT 1
        )
        WHERE d.id_lot = %s
        ORDER BY tr.ordre_affichage, tr.code_type
        """,
        (id_lot,),
    ) or []

# ════════════════════════════════════════════════════════════════
# WORKFLOW DE VALIDATION ET REJET CIBLÉ (LIGNE PAR LIGNE)
# ════════════════════════════════════════════════════════════════

def validate_donnees_batch(id_donnees_list: list, decision: str, niveau: str, 
                            user_id: int, commentaire: str = None):
    """
    Valide ou rejette un ensemble de DONNÉES.
    Chaque appel crée une NOUVELLE ligne dans validation (pas d'écrasement).
    """
    if not id_donnees_list:
        return

    statut_cible = (
        ("valide_dp" if decision == "valide" else "rejete_dp")
        if niveau == "dp"
        else ("valide_regional" if decision == "valide" else "rejete_regional")
    )

    lots_a_recalculer = set()

    for id_donnee in id_donnees_list:
        d_info = execute_query(
            "SELECT id_lot FROM app_staging.donnee_saisie WHERE id_donnee = %s",
            (id_donnee,), fetch="one"
        )
        if d_info:
            lots_a_recalculer.add(d_info["id_lot"])

        execute_insert(
            "UPDATE app_staging.donnee_saisie SET statut = %s, date_modification = CURRENT_TIMESTAMP WHERE id_donnee = %s",
            (statut_cible, id_donnee),
        )

        execute_insert(
            """
            INSERT INTO app_staging.validation 
                (id_donnee, niveau, decision, commentaire, valide_par)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (id_donnee, niveau, decision, commentaire, user_id),
        )

    for id_lot in lots_a_recalculer:
        recalculer_statut_lot(id_lot)


def submit_lot(id_lot: int, user_id: int):
    """Soumet toutes les lignes non encore validées d'un lot."""
    execute_insert(
        """
        UPDATE app_staging.donnee_saisie 
        SET statut = 'soumis', date_modification = CURRENT_TIMESTAMP
        WHERE id_lot = %s AND statut IN ('brouillon', 'rejete_dp', 'rejete_regional')
        """,
        (id_lot,),
    )
    execute_insert(
        "UPDATE app_staging.lot_saisie SET date_soumission = CURRENT_TIMESTAMP WHERE id_lot = %s",
        (id_lot,),
    )
    recalculer_statut_lot(id_lot)


def delete_draft_lot(id_lot: int):
    """Supprime un lot en brouillon."""
    execute_insert(
        "DELETE FROM app_staging.lot_saisie WHERE id_lot = %s AND statut_agrege = 'brouillon'",
        (id_lot,),
    )


# ════════════════════════════════════════════════════════════════
# CORRECTIONS ET HISTORIQUE DÉTAILLÉ
# ════════════════════════════════════════════════════════════════

def update_donnee_with_correction(id_donnee: int, field_updates: dict, user_id: int, comment_agent: str = None):
    """
    Met à jour les valeurs + historique de correction.
    NE CHANGE PAS le statut.

    Historique :
    - prioritaire : dernier rejet
    - fallback    : dernière validation (ex: valide_regional pour modif post-validation)
    """
    # 1) Dernier rejet (workflow classique rejet → correction)
    val = execute_query(
        """
        SELECT id_validation FROM app_staging.validation
        WHERE id_donnee = %s AND decision = 'rejete'
        ORDER BY date_validation DESC
        LIMIT 1
        """,
        (id_donnee,), fetch="one",
    )

    # 2) Fallback : dernière validation (workflow modif post-validation régionale)
    if not val:
        val = execute_query(
            """
            SELECT id_validation FROM app_staging.validation
            WHERE id_donnee = %s
            ORDER BY date_validation DESC
            LIMIT 1
            """,
            (id_donnee,), fetch="one",
        )

    d_info = execute_query(
        "SELECT id_lot, type_donnee FROM app_staging.donnee_saisie WHERE id_donnee = %s",
        (id_donnee,), fetch="one",
    )
    if not d_info:
        return

    type_d = d_info["type_donnee"]
    table_fille = "saisie_indicateur" if type_d == "indicateur" else "saisie_reclamation"

    current_row = execute_query(
        f"SELECT * FROM app_staging.{table_fille} WHERE id_donnee = %s",
        (id_donnee,), fetch="one",
    )

    # Historique uniquement s'il y a une validation de référence + de vrais changements
    if val and field_updates:
        real_changes = []
        for field, new_val in field_updates.items():
            # Éviter de doubler les champs dérivés des réclamations
            if field in ("nombre_reclamations", "temps_moyen_coupure_h", "delai_moyen_traitement_j") and "valeur_brute" in field_updates:
                continue

            old_val = current_row.get(field) if current_row else None
            try:
                if old_val is not None and new_val is not None and abs(float(old_val) - float(new_val)) < 0.001:
                    continue
            except (ValueError, TypeError):
                if str(old_val or "") == str(new_val or ""):
                    continue

            real_changes.append((field, old_val, new_val))

        if real_changes:
            res_c = execute_insert(
                """
                INSERT INTO app_staging.correction (id_validation, id_utilisateur, commentaire)
                VALUES (%s, %s, %s)
                RETURNING id_correction
                """,
                (val["id_validation"], user_id, comment_agent),
            )
            id_correction = res_c[0] if res_c else None

            if id_correction:
                for field, old_val, new_val in real_changes:
                    execute_insert(
                        """
                        INSERT INTO app_staging.detail_correction
                            (id_correction, champ_modifie, ancienne_valeur, nouvelle_valeur)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (id_correction, field, str(old_val) if old_val is not None else None, str(new_val) if new_val is not None else None),
                    )

    # Mise à jour des valeurs métier
    if field_updates:
        sets = ", ".join(f"{k} = %s" for k in field_updates)
        execute_insert(
            f"UPDATE app_staging.{table_fille} SET {sets} WHERE id_donnee = %s",
            tuple(field_updates.values()) + (id_donnee,),
        )

    execute_insert(
        "UPDATE app_staging.donnee_saisie SET date_modification = CURRENT_TIMESTAMP WHERE id_donnee = %s",
        (id_donnee,),
    )

def resubmit_lot_after_rejection(id_lot: int, user_id: int):
    """Resoumet un lot après correction."""
    user_role = execute_query(
        """
        SELECT r.code_role FROM app_auth.utilisateurs u
        JOIN app_auth.ref_role r ON u.id_role = r.id_role
        WHERE u.id_utilisateur = %s
        """,
        (user_id,), fetch="one",
    )
    is_admin_dp = user_role and user_role["code_role"] in ("admin_dp", "super_admin")

    lignes = execute_query(
        """
        SELECT id_donnee, statut FROM app_staging.donnee_saisie
        WHERE id_lot = %s AND statut IN ('brouillon','rejete_dp','rejete_regional','soumis')
        """,
        (id_lot,),
    ) or []

    for ligne in lignes:
        old_statut = ligne["statut"]
        id_donnee = ligne["id_donnee"]

        if old_statut not in ("rejete_dp", "rejete_regional", "brouillon"):
            if not is_admin_dp:
                continue

        if is_admin_dp:
            new_statut = "valide_dp"
            cmt = (
                "Auto-validation Admin DP après correction rejet régional"
                if old_statut == "rejete_regional"
                else "Auto-validation Admin DP après correction"
            )
            execute_insert(
                """
                INSERT INTO app_staging.validation (id_donnee, niveau, decision, commentaire, valide_par)
                VALUES (%s, 'dp', 'valide', %s, %s)
                """,
                (id_donnee, cmt, user_id),
            )
        else:
            new_statut = "soumis"

        execute_insert(
            "UPDATE app_staging.donnee_saisie SET statut = %s, date_modification = CURRENT_TIMESTAMP WHERE id_donnee = %s",
            (new_statut, id_donnee),
        )

    execute_insert(
        "UPDATE app_staging.lot_saisie SET date_soumission = CURRENT_TIMESTAMP WHERE id_lot = %s",
        (id_lot,),
    )
    recalculer_statut_lot(id_lot)


def get_lot_corrections_history(id_lot: int):
    """Historique COMPLET des corrections d'un lot."""
    return execute_query(
        """
        SELECT 
            dc.id_detail,
            c.date_correction, 
            u.nom_complet AS corrige_par_nom,
            r.libelle_role AS role_correcteur,
            COALESCE(
                ti.libelle_indicateur, 
                tr.libelle_reclamation,
                'Élément inconnu'
            ) AS element_libelle,
            v.commentaire AS motif_rejet,
            v.niveau AS niveau_rejet,
            v.date_validation AS date_rejet,
            uv.nom_complet AS rejete_par_nom,
            dc.champ_modifie,
            CASE dc.champ_modifie
                WHEN 'valeur_indicateur' THEN 'Valeur'
                WHEN 'valeur_brute' THEN 'Valeur'
                WHEN 'nombre_reclamations' THEN 'Nombre'
                WHEN 'temps_moyen_coupure_h' THEN 'Temps coupure (h)'
                WHEN 'delai_moyen_traitement_j' THEN 'Délai traitement (j)'
                WHEN 'commentaire_autre' THEN 'Commentaire Autres'
                ELSE dc.champ_modifie
            END AS champ_lisible,
            dc.ancienne_valeur, 
            dc.nouvelle_valeur
        FROM app_staging.donnee_saisie d
        JOIN app_staging.correction c ON c.id_correction IN (
            SELECT id_correction FROM app_staging.correction c2
            JOIN app_staging.validation v2 ON c2.id_validation = v2.id_validation
            WHERE v2.id_donnee = d.id_donnee
        )
        JOIN app_staging.validation v ON c.id_validation = v.id_validation
        JOIN app_staging.detail_correction dc ON c.id_correction = dc.id_correction
        JOIN app_auth.utilisateurs u ON c.id_utilisateur = u.id_utilisateur
        JOIN app_auth.ref_role r ON u.id_role = r.id_role
        LEFT JOIN app_auth.utilisateurs uv ON v.valide_par = uv.id_utilisateur
        LEFT JOIN app_staging.saisie_indicateur si ON d.id_donnee = si.id_donnee
        LEFT JOIN app_staging.ref_type_indicateur ti ON si.id_type_indicateur = ti.id_type_indicateur
        LEFT JOIN app_staging.saisie_reclamation sr ON d.id_donnee = sr.id_donnee
        LEFT JOIN app_staging.ref_type_reclamation tr ON sr.id_type_reclamation = tr.id_type_reclamation
        WHERE d.id_lot = %s
        ORDER BY c.date_correction ASC, dc.id_detail ASC
        """,
        (id_lot,),
    )


# ════════════════════════════════════════════════════════════════
# DASHBOARD STATS & RECHERCHES
# ════════════════════════════════════════════════════════════════

def get_dashboard_stats_filtered(id_province=None, annee=None, mois=None, role_view=None):
    """Statistiques par statut pour le dashboard."""
    conditions = []
    params = []

    if id_province:
        conditions.append("c.id_province = %s")
        params.append(id_province)
    if annee:
        conditions.append("per.annee = %s")
        params.append(annee)
    if mois:
        conditions.append("per.mois = %s")
        params.append(mois)

    if role_view == "admin_regional":
        conditions.append("d.statut IN ('valide_dp', 'valide_regional', 'rejete_regional')")

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    indic_stats = execute_query(
        f"""
        SELECT d.statut, COUNT(*) as count
        FROM app_staging.donnee_saisie d
        JOIN app_staging.lot_saisie l ON d.id_lot = l.id_lot
        JOIN app_staging.ref_centre c ON l.id_centre = c.id_centre
        JOIN app_staging.ref_periode per ON l.id_periode = per.id_periode
        {where} AND l.type_donnees = 'indicateurs'
        GROUP BY d.statut
        """,
        tuple(params) if params else None,
    )

    reclam_stats = execute_query(
        f"""
        SELECT d.statut, COUNT(*) as count
        FROM app_staging.donnee_saisie d
        JOIN app_staging.lot_saisie l ON d.id_lot = l.id_lot
        JOIN app_staging.ref_centre c ON l.id_centre = c.id_centre
        JOIN app_staging.ref_periode per ON l.id_periode = per.id_periode
        {where} AND l.type_donnees = 'reclamations'
        GROUP BY d.statut
        """,
        tuple(params) if params else None,
    )

    return {
        "indicateurs": {row["statut"]: row["count"] for row in (indic_stats or [])},
        "reclamations": {row["statut"]: row["count"] for row in (reclam_stats or [])},
    }


def get_province_full_stats(annee=None, mois=None, role_view=None):
    """Statistiques d'avancement complètes par province."""
    conditions = []
    params = []

    if annee:
        conditions.append("per.annee = %s")
        params.append(annee)
    if mois:
        conditions.append("per.mois = %s")
        params.append(mois)
    if role_view == "admin_regional":
        conditions.append("d.statut IN ('valide_dp', 'valide_regional', 'rejete_regional')")

    where = "AND " + " AND ".join(conditions) if conditions else ""

    return execute_query(
        f"""
        SELECT
            p.id_province, p.nom_province,
            COALESCE(SUM(CASE WHEN d.statut = 'brouillon' THEN 1 ELSE 0 END), 0) AS brouillon,
            COALESCE(SUM(CASE WHEN d.statut = 'soumis' THEN 1 ELSE 0 END), 0) AS soumis,
            COALESCE(SUM(CASE WHEN d.statut = 'valide_dp' THEN 1 ELSE 0 END), 0) AS valide_dp,
            COALESCE(SUM(CASE WHEN d.statut = 'rejete_dp' THEN 1 ELSE 0 END), 0) AS rejete_dp,
            COALESCE(SUM(CASE WHEN d.statut = 'valide_regional' THEN 1 ELSE 0 END), 0) AS valide_regional,
            COALESCE(SUM(CASE WHEN d.statut = 'rejete_regional' THEN 1 ELSE 0 END), 0) AS rejete_regional,
            COUNT(d.id_donnee) AS total
        FROM app_staging.ref_province p
        LEFT JOIN app_staging.ref_centre c ON p.id_province = c.id_province
        LEFT JOIN app_staging.lot_saisie l ON c.id_centre = l.id_centre
        LEFT JOIN app_staging.ref_periode per ON l.id_periode = per.id_periode
        LEFT JOIN app_staging.donnee_saisie d ON l.id_lot = d.id_lot {where}
        GROUP BY p.id_province, p.nom_province
        ORDER BY p.id_province
        """,
        tuple(params) if params else None,
    )


def get_activity_timeline(annee=None, mois=None, id_province=None, role_view=None, statut=None):
    """Courbe d'activité mensuelle par province."""
    conditions = []
    params = []

    if annee:
        conditions.append("per.annee = %s")
        params.append(annee)
    if mois:
        conditions.append("per.mois = %s")
        params.append(mois)
    if id_province:
        conditions.append("c.id_province = %s")
        params.append(id_province)
    if statut:
        conditions.append("d.statut = %s")
        params.append(statut)
    elif role_view == "admin_regional":
        conditions.append("d.statut IN ('valide_dp', 'valide_regional', 'rejete_regional')")

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    return execute_query(
        f"""
        SELECT 
            p.nom_province, p.id_province, per.annee, per.mois,
            COUNT(d.id_donnee) AS nb_total
        FROM app_staging.donnee_saisie d
        JOIN app_staging.lot_saisie l ON d.id_lot = l.id_lot
        JOIN app_staging.ref_centre c ON l.id_centre = c.id_centre
        JOIN app_staging.ref_province p ON c.id_province = p.id_province
        JOIN app_staging.ref_periode per ON l.id_periode = per.id_periode
        {where}
        GROUP BY p.nom_province, p.id_province, per.annee, per.mois
        ORDER BY per.annee, per.mois, p.nom_province
        """,
        tuple(params) if params else None,
    )


def get_available_years_dashboard():
    """Récupère la liste des années saisies."""
    res = execute_query("SELECT DISTINCT annee FROM app_staging.ref_periode ORDER BY annee DESC")
    return [r["annee"] for r in (res or [])]


# ════════════════════════════════════════════════════════════════
# AUDIT LOGS
# ════════════════════════════════════════════════════════════════

def get_audit_logs(user_id=None, id_province=None, annee=None, mois=None, limit=500):
    """Récupère les logs d'audit avec filtres."""
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

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    params.append(limit)

    return execute_query(
        f"""
        SELECT al.*, u.nom_complet, u.username, r.libelle_role AS role, p.code_province, u.id_province
        FROM app_auth.audit_logs al
        JOIN app_auth.utilisateurs u ON al.id_utilisateur = u.id_utilisateur
        JOIN app_auth.ref_role r ON u.id_role = r.id_role
        LEFT JOIN app_staging.ref_province p ON u.id_province = p.id_province
        {where}
        ORDER BY al.date_action DESC
        LIMIT %s
        """,
        tuple(params),
    )


def get_audit_available_years():
    res = execute_query("SELECT DISTINCT EXTRACT(YEAR FROM date_action)::int AS annee FROM app_auth.audit_logs ORDER BY annee DESC")
    return [r["annee"] for r in (res or [])]


def get_audit_available_users():
    return execute_query(
        """
        SELECT u.id_utilisateur, u.username, u.nom_complet, r.libelle_role AS role, p.code_province, u.est_actif
        FROM app_auth.utilisateurs u
        JOIN app_auth.ref_role r ON u.id_role = r.id_role
        LEFT JOIN app_staging.ref_province p ON u.id_province = p.id_province
        ORDER BY r.id_role, p.code_province NULLS FIRST, u.nom_complet
        """
    )


def get_dp_activity_summary(annee=None, mois=None, id_province=None, role_view=None):
    """Vue globale d'activité par DP."""
    conditions = []
    params = []

    if annee:
        conditions.append("per.annee = %s")
        params.append(annee)
    if mois:
        conditions.append("per.mois = %s")
        params.append(mois)
    if role_view == "admin_regional":
        conditions.append("d.statut IN ('valide_dp', 'valide_regional', 'rejete_regional')")

    where_inner = "AND " + " AND ".join(conditions) if conditions else ""
    
    where_outer = ""
    outer_params = []
    if id_province:
        where_outer = "WHERE p.id_province = %s"
        outer_params.append(id_province)

    return execute_query(
        f"""
        SELECT 
            p.id_province, p.nom_province,
            COUNT(d.id_donnee) FILTER (WHERE d.type_donnee = 'indicateur') AS nb_indicateurs,
            COUNT(d.id_donnee) FILTER (WHERE d.type_donnee LIKE 'reclamation%%') AS nb_reclamations,
            COUNT(d.id_donnee) AS nb_total,
            MAX(d.date_modification) AS derniere_saisie,
            COUNT(d.id_donnee) FILTER (WHERE d.statut = 'valide_regional') AS nb_valides,
            COUNT(d.id_donnee) FILTER (WHERE d.statut IN ('soumis', 'valide_dp')) AS nb_soumis
        FROM app_staging.ref_province p
        LEFT JOIN app_staging.ref_centre c ON p.id_province = c.id_province
        LEFT JOIN app_staging.lot_saisie l ON c.id_centre = l.id_centre
        LEFT JOIN app_staging.ref_periode per ON l.id_periode = per.id_periode
        LEFT JOIN app_staging.donnee_saisie d ON l.id_lot = d.id_lot {where_inner}
        {where_outer}
        GROUP BY p.id_province, p.nom_province
        ORDER BY p.id_province
        """,
        tuple(params + outer_params) if params or outer_params else None,
    )


def get_reference_totals():
    """Totaux des types actifs pour le calcul de complétude."""
    indic = execute_query("SELECT COUNT(*) as cnt FROM app_staging.ref_type_indicateur WHERE est_actif = TRUE", fetch="one")
    reclam = execute_query("SELECT COUNT(*) as cnt FROM app_staging.ref_type_reclamation WHERE est_actif = TRUE", fetch="one")
    return {
        "total_types_indic": indic["cnt"] if indic else 0,
        "total_types_reclam": reclam["cnt"] if reclam else 0,
    }


def get_dp_final_validated_summary(annee=None, mois=None):
    """
    Agrégation par DP UNIQUEMENT des données validées définitivement (valide_regional).
    """
    conditions = ["d.statut = 'valide_regional'"]
    params = []
    if annee:
        conditions.append("per.annee = %s")
        params.append(annee)
    if mois:
        conditions.append("per.mois = %s")
        params.append(mois)
    
    where = "WHERE " + " AND ".join(conditions)

    return execute_query(
        f"""
        SELECT 
            p.id_province, p.nom_province,
            COUNT(d.id_donnee) FILTER (WHERE d.type_donnee = 'indicateur') AS nb_indicateurs,
            COUNT(d.id_donnee) FILTER (WHERE d.type_donnee LIKE 'reclamation%%') AS nb_reclamations
        FROM app_staging.ref_province p
        LEFT JOIN app_staging.ref_centre c ON p.id_province = c.id_province
        LEFT JOIN app_staging.lot_saisie l ON c.id_centre = l.id_centre
        LEFT JOIN app_staging.ref_periode per ON l.id_periode = per.id_periode
        LEFT JOIN app_staging.donnee_saisie d ON l.id_lot = d.id_lot
        {where}
        GROUP BY p.id_province, p.nom_province
        ORDER BY p.id_province
        """,
        tuple(params) if params else None
    )


def set_lot_commentaire_global(id_lot: int, commentaire: str, niveau: str, user_id: int):
    """Stocke le commentaire global de l'admin sur le lot."""
    from auth.authentication import AuthManager
    AuthManager.log_action(
        user_id, 
        f"COMMENTAIRE_LOT_{niveau.upper()}", 
        "lot_saisie", 
        id_lot, 
        {"commentaire": commentaire, "niveau": niveau}
    )


def get_lot_commentaire_global(id_lot: int, niveau: str = None):
    """Récupère le dernier commentaire global posé sur un lot."""
    action_filter = f"AND action = 'COMMENTAIRE_LOT_{niveau.upper()}'" if niveau else "AND action LIKE 'COMMENTAIRE_LOT_%'"
    
    result = execute_query(
        f"""
        SELECT details, action, date_action, u.nom_complet AS admin_nom
        FROM app_auth.audit_logs al
        JOIN app_auth.utilisateurs u ON al.id_utilisateur = u.id_utilisateur
        WHERE al.table_cible = 'lot_saisie' 
          AND al.id_enregistrement = %s
          {action_filter}
        ORDER BY al.date_action DESC
        LIMIT 1
        """,
        (id_lot,), fetch="one"
    )
    
    if result and result["details"]:
        return {
            "commentaire": result["details"].get("commentaire", ""),
            "niveau": result["details"].get("niveau", ""),
            "admin_nom": result["admin_nom"],
            "date": result["date_action"]
        }
    return None


# ════════════════════════════════════════════════════════════════
# TRANSFERTS ADMIN_DP → AGENT_DP (après rejet régional)
# ════════════════════════════════════════════════════════════════

def transfert_lot_a_agent(id_lot: int, id_admin_dp: int, commentaire: str = None):
    """L'admin DP transfère un lot rejeté par le régional à l'agent d'origine."""
    execute_insert(
        """
        INSERT INTO app_staging.transfert_agent (id_lot, id_admin_dp, commentaire)
        VALUES (%s, %s, %s)
        """,
        (id_lot, id_admin_dp, commentaire)
    )


def get_transfert_actif_lot(id_lot: int):
    """Récupère le transfert actif (non traité) pour un lot."""
    return execute_query(
        """
        SELECT t.*, u.nom_complet AS admin_dp_nom
        FROM app_staging.transfert_agent t
        JOIN app_auth.utilisateurs u ON t.id_admin_dp = u.id_utilisateur
        WHERE t.id_lot = %s AND t.traite = FALSE
        ORDER BY t.date_transfert DESC
        LIMIT 1
        """,
        (id_lot,), fetch="one"
    )


def marquer_transfert_traite(id_lot: int):
    """Marque le transfert actif comme traité (quand l'agent resoumet)."""
    execute_insert(
        """
        UPDATE app_staging.transfert_agent
        SET traite = TRUE, date_traitement = CURRENT_TIMESTAMP
        WHERE id_lot = %s AND traite = FALSE
        """,
        (id_lot,)
    )


def get_lots_rejets_regional_pour_admin_dp(id_province: int, type_donnees: str):
    """Récupère les lots rejetés par le régional QUE L'ADMIN DP DOIT TRAITER."""
    return execute_query(
        """
        SELECT 
            l.id_lot, l.id_centre, c.nom_centre, c.id_province, p.nom_province, p.code_province,
            per.annee, per.mois, l.type_donnees, l.statut_agrege AS statut,
            l.cree_par, u.nom_complet AS cree_par_nom,
            l.date_creation, l.date_soumission,
            COUNT(d.id_donnee) AS nb_enregistrements
        FROM app_staging.lot_saisie l
        JOIN app_staging.ref_centre c ON l.id_centre = c.id_centre
        JOIN app_staging.ref_province p ON c.id_province = p.id_province
        JOIN app_staging.ref_periode per ON l.id_periode = per.id_periode
        JOIN app_auth.utilisateurs u ON l.cree_par = u.id_utilisateur
        LEFT JOIN app_staging.donnee_saisie d ON l.id_lot = d.id_lot
        WHERE l.type_donnees = %s
          AND c.id_province = %s
          AND l.statut_agrege = 'partiellement_rejete_regional'
          AND NOT EXISTS (
              SELECT 1 FROM app_staging.transfert_agent t
              WHERE t.id_lot = l.id_lot AND t.traite = FALSE
          )
        GROUP BY l.id_lot, c.nom_centre, c.id_province, p.nom_province, p.code_province,
                 per.annee, per.mois, u.nom_complet
        ORDER BY l.date_creation DESC
        """,
        (type_donnees, id_province)
    )


def get_lots_transferes_pour_agent(id_province: int, user_id: int, type_donnees: str):
    """Récupère les lots transférés par admin DP à un agent spécifique."""
    return execute_query(
        """
        SELECT 
            l.id_lot, l.id_centre, c.nom_centre, c.id_province, p.nom_province, p.code_province,
            per.annee, per.mois, l.type_donnees, l.statut_agrege AS statut,
            l.cree_par, u.nom_complet AS cree_par_nom,
            l.date_creation, l.date_soumission,
            COUNT(d.id_donnee) AS nb_enregistrements,
            t.commentaire AS commentaire_transfert,
            uad.nom_complet AS admin_dp_nom
        FROM app_staging.lot_saisie l
        JOIN app_staging.ref_centre c ON l.id_centre = c.id_centre
        JOIN app_staging.ref_province p ON c.id_province = p.id_province
        JOIN app_staging.ref_periode per ON l.id_periode = per.id_periode
        JOIN app_auth.utilisateurs u ON l.cree_par = u.id_utilisateur
        JOIN app_staging.transfert_agent t ON l.id_lot = t.id_lot AND t.traite = FALSE
        JOIN app_auth.utilisateurs uad ON t.id_admin_dp = uad.id_utilisateur
        LEFT JOIN app_staging.donnee_saisie d ON l.id_lot = d.id_lot
        WHERE l.type_donnees = %s
          AND c.id_province = %s
          AND l.cree_par = %s
        GROUP BY l.id_lot, c.nom_centre, c.id_province, p.nom_province, p.code_province,
                 per.annee, per.mois, u.nom_complet, t.commentaire, uad.nom_complet
        ORDER BY l.date_creation DESC
        """,
        (type_donnees, id_province, user_id)
    )


# ════════════════════════════════════════════════════════════════
# HISTORIQUE ENRICHI
# ════════════════════════════════════════════════════════════════

def get_lot_rejets_history(id_lot: int):
    """Historique COMPLET de tous les rejets successifs d'un lot."""
    return execute_query(
        """
        SELECT 
            v.id_validation,
            v.date_validation,
            v.niveau,
            v.commentaire AS motif,
            u.nom_complet AS rejete_par_nom,
            r.libelle_role AS rejete_par_role,
            COALESCE(
                ti.libelle_indicateur, 
                tr.libelle_reclamation,
                'Élément inconnu'
            ) AS element_libelle,
            d.id_donnee
        FROM app_staging.donnee_saisie d
        JOIN app_staging.validation v ON d.id_donnee = v.id_donnee
        JOIN app_auth.utilisateurs u ON v.valide_par = u.id_utilisateur
        JOIN app_auth.ref_role r ON u.id_role = r.id_role
        LEFT JOIN app_staging.saisie_indicateur si ON d.id_donnee = si.id_donnee
        LEFT JOIN app_staging.ref_type_indicateur ti ON si.id_type_indicateur = ti.id_type_indicateur
        LEFT JOIN app_staging.saisie_reclamation sr ON d.id_donnee = sr.id_donnee
        LEFT JOIN app_staging.ref_type_reclamation tr ON sr.id_type_reclamation = tr.id_type_reclamation
        WHERE d.id_lot = %s AND v.decision = 'rejete'
        ORDER BY v.date_validation ASC, d.id_donnee
        """,
        (id_lot,)
    )


def get_lot_commentaires_globaux(id_lot: int):
    """Récupère TOUS les commentaires généraux successifs postés sur un lot."""
    result = execute_query(
        """
        SELECT 
            al.details, 
            al.action, 
            al.date_action, 
            u.nom_complet AS admin_nom,
            r.libelle_role AS admin_role
        FROM app_auth.audit_logs al
        JOIN app_auth.utilisateurs u ON al.id_utilisateur = u.id_utilisateur
        JOIN app_auth.ref_role r ON u.id_role = r.id_role
        WHERE al.table_cible = 'lot_saisie' 
          AND al.id_enregistrement = %s
          AND al.action LIKE 'COMMENTAIRE_LOT_%%'
        ORDER BY al.date_action ASC
        """,
        (id_lot,)
    )
    return result or []


def get_lot_commentaires_correction(id_lot: int):
    """Récupère les commentaires d'explication de l'agent lors des corrections."""
    return execute_query(
        """
        SELECT DISTINCT
            c.date_correction,
            c.commentaire,
            u.nom_complet AS agent_nom,
            r.libelle_role AS agent_role
        FROM app_staging.correction c
        JOIN app_staging.validation v ON c.id_validation = v.id_validation
        JOIN app_staging.donnee_saisie d ON v.id_donnee = d.id_donnee
        JOIN app_auth.utilisateurs u ON c.id_utilisateur = u.id_utilisateur
        JOIN app_auth.ref_role r ON u.id_role = r.id_role
        WHERE d.id_lot = %s AND c.commentaire IS NOT NULL AND c.commentaire != ''
        ORDER BY c.date_correction ASC
        """,
        (id_lot,)
    )


def get_lot_createur_role(id_lot: int) -> str:
    """Retourne le code_role du créateur d'un lot."""
    result = execute_query(
        """
        SELECT r.code_role
        FROM app_staging.lot_saisie l
        JOIN app_auth.utilisateurs u ON l.cree_par = u.id_utilisateur
        JOIN app_auth.ref_role r ON u.id_role = r.id_role
        WHERE l.id_lot = %s
        """,
        (id_lot,), fetch="one"
    )
    return result["code_role"] if result else None


def get_dp_completion_and_activity(id_province=None, role_view=None):
    """
    Complétude par province :
    - nombre de types d'indicateurs DISTINCTS déjà saisis
    - nombre de types de réclamations DISTINCTS déjà saisis
    """
    status_sql = ""
    if role_view == "admin_regional":
        status_sql = "AND d.statut IN ('valide_dp', 'valide_regional', 'rejete_regional', 'soumis')"

    params = []
    prov_sql = ""
    if id_province is not None:
        prov_sql = "WHERE p.id_province = %s"
        params.append(id_province)

    query = f"""
        SELECT
            p.id_province,
            COALESCE((
                SELECT COUNT(DISTINCT si.id_type_indicateur)
                FROM app_staging.donnee_saisie d
                JOIN app_staging.saisie_indicateur si ON si.id_donnee = d.id_donnee
                JOIN app_staging.lot_saisie l ON l.id_lot = d.id_lot
                JOIN app_staging.ref_centre c ON c.id_centre = l.id_centre
                WHERE c.id_province = p.id_province
                {status_sql}
            ), 0) AS types_indic_saisis,
            COALESCE((
                SELECT COUNT(DISTINCT sr.id_type_reclamation)
                FROM app_staging.donnee_saisie d
                JOIN app_staging.saisie_reclamation sr ON sr.id_donnee = d.id_donnee
                JOIN app_staging.lot_saisie l ON l.id_lot = d.id_lot
                JOIN app_staging.ref_centre c ON c.id_centre = l.id_centre
                WHERE c.id_province = p.id_province
                {status_sql}
            ), 0) AS types_reclam_saisis
        FROM app_staging.ref_province p
        {prov_sql}
        ORDER BY p.id_province
    """

    return execute_query(query, tuple(params) if params else None) or []





# ════════════════════════════════════════════════════════════════
# MODIFICATION POST-VALIDATION RÉGIONAL (Workflow de délégation)
# ════════════════════════════════════════════════════════════════

def demander_modification_lot(id_lot: int, id_demandeur: int, role_demandeur: str,
                                id_destinataire: int, role_destinataire: str,
                                commentaire: str, only_ids: list = None):
    """
    Créer une demande de modification sur un lot déjà validé régional.
    - only_ids : liste optionnelle de id_donnee à modifier (sinon toutes les lignes)
    """
    nouveau_statut = "modif_admin_dp" if role_destinataire == "admin_dp" else "modif_agent_dp"

    # Changer le statut des lignes concernées
    if only_ids:
        for id_donnee in only_ids:
            execute_insert(
                "UPDATE app_staging.donnee_saisie SET statut = %s, date_modification = CURRENT_TIMESTAMP WHERE id_donnee = %s",
                (nouveau_statut, id_donnee)
            )
    else:
        execute_insert(
            """
            UPDATE app_staging.donnee_saisie 
            SET statut = %s, date_modification = CURRENT_TIMESTAMP 
            WHERE id_lot = %s AND statut = 'valide_regional'
            """,
            (nouveau_statut, id_lot)
        )

    # Créer la demande
    execute_insert(
        """
        INSERT INTO app_staging.demande_modification 
            (id_lot, id_demandeur, role_demandeur, id_destinataire, role_destinataire, commentaire)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (id_lot, id_demandeur, role_demandeur, id_destinataire, role_destinataire, commentaire)
    )

    recalculer_statut_lot(id_lot)


def get_demandes_pour_user(user_id: int, type_donnees: str):
    """Récupère les lots en cours de modification pour cet utilisateur (admin_dp OU agent)."""
    return execute_query(
        """
        SELECT DISTINCT
            l.id_lot, l.id_centre, c.nom_centre, c.id_province, p.nom_province, p.code_province,
            per.annee, per.mois, l.type_donnees, l.statut_agrege AS statut,
            l.cree_par, u.nom_complet AS cree_par_nom,
            l.date_creation, l.date_soumission,
            COUNT(d.id_donnee) AS nb_enregistrements,
            dm.commentaire AS commentaire_demande,
            ud.nom_complet AS demandeur_nom,
            dm.role_demandeur,
            dm.date_demande
        FROM app_staging.lot_saisie l
        JOIN app_staging.ref_centre c ON l.id_centre = c.id_centre
        JOIN app_staging.ref_province p ON c.id_province = p.id_province
        JOIN app_staging.ref_periode per ON l.id_periode = per.id_periode
        JOIN app_auth.utilisateurs u ON l.cree_par = u.id_utilisateur
        JOIN app_staging.demande_modification dm ON l.id_lot = dm.id_lot
        JOIN app_auth.utilisateurs ud ON dm.id_demandeur = ud.id_utilisateur
        LEFT JOIN app_staging.donnee_saisie d ON l.id_lot = d.id_lot
        WHERE l.type_donnees = %s
          AND dm.id_destinataire = %s
          AND dm.statut = 'en_attente'
        GROUP BY l.id_lot, c.nom_centre, c.id_province, p.nom_province, p.code_province,
                 per.annee, per.mois, u.nom_complet, dm.commentaire, ud.nom_complet, 
                 dm.role_demandeur, dm.date_demande
        ORDER BY dm.date_demande DESC
        """,
        (type_donnees, user_id)
    )


def marquer_demandes_traitees(id_lot: int, id_destinataire: int = None):
    """Marque les demandes en attente d'un lot comme traitées."""
    if id_destinataire:
        execute_insert(
            """
            UPDATE app_staging.demande_modification
            SET statut = 'traite', date_traitement = CURRENT_TIMESTAMP
            WHERE id_lot = %s AND id_destinataire = %s AND statut = 'en_attente'
            """,
            (id_lot, id_destinataire)
        )
    else:
        execute_insert(
            """
            UPDATE app_staging.demande_modification
            SET statut = 'traite', date_traitement = CURRENT_TIMESTAMP
            WHERE id_lot = %s AND statut = 'en_attente'
            """,
            (id_lot,)
        )


def get_admin_dp_de_province(id_province: int):
    """Retourne l'admin_dp actif de la province."""
    return execute_query(
        """
        SELECT u.id_utilisateur, u.nom_complet
        FROM app_auth.utilisateurs u
        JOIN app_auth.ref_role r ON u.id_role = r.id_role
        WHERE r.code_role = 'admin_dp'
          AND u.id_province = %s
          AND u.est_actif = TRUE
        LIMIT 1
        """,
        (id_province,), fetch="one"
    )


def modifier_et_valider_regional(id_donnee: int, updates: dict, user_id: int):
    """L'admin_regional modifie une donnée déjà validée + auto-revalide régional."""
    update_donnee_with_correction(id_donnee, updates, user_id, "Modification par Admin Régional (post-validation)")
    execute_insert(
        """
        INSERT INTO app_staging.validation 
            (id_donnee, niveau, decision, commentaire, valide_par)
        VALUES (%s, 'regional', 'valide', 'Re-validation après modification admin régional', %s)
        """,
        (id_donnee, user_id)
    )


def resoumettre_apres_modif_admin_dp(id_lot: int, user_id: int):
    """L'admin_dp finit sa modification → auto-valide DP → attend re-validation régionale."""
    lignes = execute_query(
        "SELECT id_donnee FROM app_staging.donnee_saisie WHERE id_lot = %s AND statut = 'modif_admin_dp'",
        (id_lot,)
    ) or []

    for l in lignes:
        execute_insert(
            "UPDATE app_staging.donnee_saisie SET statut = 'valide_dp', date_modification = CURRENT_TIMESTAMP WHERE id_donnee = %s",
            (l["id_donnee"],)
        )
        execute_insert(
            """
            INSERT INTO app_staging.validation 
                (id_donnee, niveau, decision, commentaire, valide_par)
            VALUES (%s, 'dp', 'valide', 'Auto-validation après modification demandée par régional', %s)
            """,
            (l["id_donnee"], user_id)
        )

    marquer_demandes_traitees(id_lot, user_id)
    recalculer_statut_lot(id_lot)


def resoumettre_apres_modif_agent(id_lot: int, user_id: int):
    """L'agent finit sa modification → soumis → attend validation admin_dp."""
    execute_insert(
        """
        UPDATE app_staging.donnee_saisie 
        SET statut = 'soumis', date_modification = CURRENT_TIMESTAMP
        WHERE id_lot = %s AND statut = 'modif_agent_dp'
        """,
        (id_lot,)
    )
    marquer_demandes_traitees(id_lot, user_id)
    recalculer_statut_lot(id_lot)







# ════════════════════════════════════════════════════════════════
# HISTORIQUE OPTIMISÉ (Par donnée, à la demande)
# ════════════════════════════════════════════════════════════════

def get_donnees_avec_corrections(id_lot: int):
    """
    Retourne la liste des données du lot ayant AU MOINS une correction.
    Utilisé pour l'affichage compact de l'historique.
    """
    return execute_query(
        """
        SELECT DISTINCT
            d.id_donnee,
            COALESCE(ti.libelle_indicateur, tr.libelle_reclamation, 'Élément inconnu') AS element_libelle,
            COALESCE(ti.code_indicateur, tr.code_type, '—') AS element_code,
            d.statut,
            (
                SELECT COUNT(*) 
                FROM app_staging.correction c2
                JOIN app_staging.validation v2 ON c2.id_validation = v2.id_validation
                WHERE v2.id_donnee = d.id_donnee
            ) AS nb_corrections,
            (
                SELECT MAX(c3.date_correction)
                FROM app_staging.correction c3
                JOIN app_staging.validation v3 ON c3.id_validation = v3.id_validation
                WHERE v3.id_donnee = d.id_donnee
            ) AS derniere_correction
        FROM app_staging.donnee_saisie d
        LEFT JOIN app_staging.saisie_indicateur si ON d.id_donnee = si.id_donnee
        LEFT JOIN app_staging.ref_type_indicateur ti ON si.id_type_indicateur = ti.id_type_indicateur
        LEFT JOIN app_staging.saisie_reclamation sr ON d.id_donnee = sr.id_donnee
        LEFT JOIN app_staging.ref_type_reclamation tr ON sr.id_type_reclamation = tr.id_type_reclamation
        WHERE d.id_lot = %s
          AND EXISTS (
              SELECT 1 
              FROM app_staging.correction c
              JOIN app_staging.validation v ON c.id_validation = v.id_validation
              WHERE v.id_donnee = d.id_donnee
          )
        ORDER BY derniere_correction DESC
        """,
        (id_lot,)
    ) or []


def get_historique_correction_donnee(id_donnee: int):
    """
    Retourne l'historique COMPLET des corrections d'UNE donnée spécifique.
    """
    return execute_query(
        """
        SELECT 
            dc.id_detail,
            c.date_correction, 
            u.nom_complet AS corrige_par_nom,
            r.libelle_role AS role_correcteur,
            v.commentaire AS motif_rejet,
            v.niveau AS niveau_rejet,
            v.date_validation AS date_rejet,
            v.decision AS decision_validation,
            uv.nom_complet AS rejete_par_nom,
            dc.champ_modifie,
            CASE dc.champ_modifie
                WHEN 'valeur_indicateur' THEN 'Valeur'
                WHEN 'valeur_brute' THEN 'Valeur'
                WHEN 'nombre_reclamations' THEN 'Nombre'
                WHEN 'temps_moyen_coupure_h' THEN 'Temps coupure (h)'
                WHEN 'delai_moyen_traitement_j' THEN 'Délai traitement (j)'
                WHEN 'commentaire_autre' THEN 'Commentaire Autres'
                ELSE dc.champ_modifie
            END AS champ_lisible,
            dc.ancienne_valeur, 
            dc.nouvelle_valeur,
            c.commentaire AS commentaire_correcteur
        FROM app_staging.correction c
        JOIN app_staging.validation v ON c.id_validation = v.id_validation
        JOIN app_staging.detail_correction dc ON c.id_correction = dc.id_correction
        JOIN app_auth.utilisateurs u ON c.id_utilisateur = u.id_utilisateur
        JOIN app_auth.ref_role r ON u.id_role = r.id_role
        LEFT JOIN app_auth.utilisateurs uv ON v.valide_par = uv.id_utilisateur
        WHERE v.id_donnee = %s
        ORDER BY c.date_correction DESC, dc.id_detail ASC
        """,
        (id_donnee,)
    ) or []










# ════════════════════════════════════════════════════════════════
# HISTORIQUE OPTIMISÉ V2 : Marquage inline dans le tableau
# ════════════════════════════════════════════════════════════════

def get_ids_donnees_modifiees(id_lot: int) -> set:
    """
    Retourne l'ensemble des id_donnee du lot ayant au moins une correction.
    Utilisé pour marquer visuellement les données modifiées.
    """
    rows = execute_query(
        """
        SELECT DISTINCT v.id_donnee
        FROM app_staging.donnee_saisie d
        JOIN app_staging.validation v ON d.id_donnee = v.id_donnee
        JOIN app_staging.correction c ON c.id_validation = v.id_validation
        WHERE d.id_lot = %s
        """,
        (id_lot,)
    ) or []
    return {r["id_donnee"] for r in rows}