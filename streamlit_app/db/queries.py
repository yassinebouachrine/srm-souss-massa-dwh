"""
SRM Souss-Massa - Requetes SQL avec workflow de validation
"""

import pandas as pd
from streamlit_app.db.connection import get_engine, get_db_connection


def get_provinces():
    engine = get_engine()
    return pd.read_sql(
        "SELECT id_province, code_province, nom_province FROM gold.dim_province ORDER BY nom_province",
        engine
    )


def get_centres(id_province=None):
    engine = get_engine()
    if id_province:
        return pd.read_sql(
            "SELECT id_centre, code_centre, nom_centre FROM gold.dim_centre WHERE id_province = %(p)s ORDER BY nom_centre",
            engine, params={'p': id_province}
        )
    return pd.read_sql(
        "SELECT id_centre, code_centre, nom_centre, id_province FROM gold.dim_centre ORDER BY nom_centre",
        engine
    )


def get_types_indicateurs():
    engine = get_engine()
    return pd.read_sql(
        "SELECT * FROM gold.dim_type_indicateur_dp ORDER BY ordre_affichage",
        engine
    )


def get_types_reclamations():
    engine = get_engine()
    return pd.read_sql(
        "SELECT * FROM gold.dim_type_reclamation ORDER BY ordre_affichage",
        engine
    )


def get_etages():
    engine = get_engine()
    return pd.read_sql(
        "SELECT * FROM gold.dim_etage_pression ORDER BY nom_etage",
        engine
    )


def insert_indicateur_dp(data):
    """
    Insert indicateur avec statut EN_ATTENTE (doit etre valide par directeur)
    Sauf si l'utilisateur est directeur/admin -> VALIDE directement
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO staging.indicateurs_dp
                (id_province, id_centre, code_indicateur,
                 annee, mois, valeur, commentaire, saisi_par, statut)
            VALUES
                (%(id_province)s, %(id_centre)s, %(code_indicateur)s,
                 %(annee)s, %(mois)s, %(valeur)s, %(commentaire)s,
                 %(saisi_par)s, %(statut)s)
            ON CONFLICT (id_province, id_centre, code_indicateur, annee, mois)
            DO UPDATE SET
                valeur = EXCLUDED.valeur,
                commentaire = EXCLUDED.commentaire,
                statut = EXCLUDED.statut,
                modifie_par = EXCLUDED.saisi_par,
                date_modification = NOW()
            RETURNING id_saisie, (xmax = 0) AS inserted
        """, data)
        result = cur.fetchone()
        conn.commit()
        return result['id_saisie'], result['inserted']


def insert_reclamation_dp(data):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO staging.reclamations_dp
                (id_province, id_centre, code_type_reclam,
                 annee, mois, nombre, temps_coupure_h, delai_traitement_j,
                 commentaire, saisi_par, statut)
            VALUES
                (%(id_province)s, %(id_centre)s, %(code_type_reclam)s,
                 %(annee)s, %(mois)s, %(nombre)s, %(temps_coupure_h)s,
                 %(delai_traitement_j)s, %(commentaire)s, %(saisi_par)s, %(statut)s)
            ON CONFLICT (id_province, id_centre, code_type_reclam, annee, mois)
            DO UPDATE SET
                nombre = EXCLUDED.nombre,
                temps_coupure_h = EXCLUDED.temps_coupure_h,
                delai_traitement_j = EXCLUDED.delai_traitement_j,
                statut = EXCLUDED.statut,
                modifie_par = EXCLUDED.saisi_par,
                date_modification = NOW()
            RETURNING id_saisie, (xmax = 0) AS inserted
        """, data)
        result = cur.fetchone()
        conn.commit()
        return result['id_saisie'], result['inserted']


def insert_rendement_etage(data):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO staging.rendements_etage
                (id_etage, annee, mois, nombre_clients,
                 volume_facture_m3, volume_amene_m3, rendement,
                 commentaire, saisi_par, statut)
            VALUES
                (%(id_etage)s, %(annee)s, %(mois)s, %(nombre_clients)s,
                 %(volume_facture_m3)s, %(volume_amene_m3)s, %(rendement)s,
                 %(commentaire)s, %(saisi_par)s, %(statut)s)
            ON CONFLICT (id_etage, annee, mois)
            DO UPDATE SET
                nombre_clients = EXCLUDED.nombre_clients,
                volume_facture_m3 = EXCLUDED.volume_facture_m3,
                volume_amene_m3 = EXCLUDED.volume_amene_m3,
                rendement = EXCLUDED.rendement,
                statut = EXCLUDED.statut,
                modifie_par = EXCLUDED.saisi_par,
                date_modification = NOW()
            RETURNING id_saisie, (xmax = 0) AS inserted
        """, data)
        result = cur.fetchone()
        conn.commit()
        return result['id_saisie'], result['inserted']


def get_indicateurs_saisis(id_province, id_centre, annee, mois):
    engine = get_engine()
    query = """
        SELECT code_indicateur, valeur, statut
        FROM staging.indicateurs_dp
        WHERE id_province = %(p)s
          AND (id_centre = %(c)s OR (id_centre IS NULL AND %(c)s IS NULL))
          AND annee = %(a)s AND mois = %(m)s
    """
    df = pd.read_sql(query, engine, params={'p': id_province, 'c': id_centre, 'a': annee, 'm': mois})
    return dict(zip(df['code_indicateur'], df['valeur']))


def get_saisies_en_attente(id_province=None):
    """Recuperer les saisies en attente de validation"""
    engine = get_engine()
    query = """
        SELECT s.id_saisie, s.id_province, p.nom_province,
               s.code_indicateur, t.libelle_indicateur, t.unite,
               s.annee, s.mois, s.valeur, s.saisi_par, s.date_saisie, s.statut
        FROM staging.indicateurs_dp s
        JOIN gold.dim_province p ON s.id_province = p.id_province
        JOIN gold.dim_type_indicateur_dp t ON s.code_indicateur = t.code_indicateur
        WHERE s.statut = 'EN_ATTENTE'
    """
    params = {}
    if id_province:
        query += " AND s.id_province = %(p)s"
        params['p'] = id_province
    
    query += " ORDER BY s.date_saisie DESC"
    return pd.read_sql(query, engine, params=params)


def valider_saisie(id_saisie, valideur):
    """Valider une saisie (par directeur)"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE staging.indicateurs_dp
            SET statut = 'VALIDE',
                modifie_par = %s,
                date_modification = NOW()
            WHERE id_saisie = %s AND statut = 'EN_ATTENTE'
            RETURNING id_saisie
        """, (valideur, id_saisie))
        result = cur.fetchone()
        conn.commit()
        return result is not None


def rejeter_saisie(id_saisie, valideur, raison):
    """Rejeter une saisie"""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE staging.indicateurs_dp
            SET statut = 'REJETE',
                commentaire = COALESCE(commentaire, '') || ' [REJETE: ' || %s || ']',
                modifie_par = %s,
                date_modification = NOW()
            WHERE id_saisie = %s AND statut = 'EN_ATTENTE'
            RETURNING id_saisie
        """, (raison, valideur, id_saisie))
        result = cur.fetchone()
        conn.commit()
        return result is not None


def get_historique_saisies(id_province, id_centre=None, limit=50):
    engine = get_engine()
    query = """
        SELECT s.annee, s.mois, t.libelle_indicateur AS indicateur, t.unite,
               s.valeur, s.statut, s.saisi_par, s.date_saisie,
               CASE WHEN s.est_traite THEN 'Integre' ELSE 'En attente' END AS traitement
        FROM staging.indicateurs_dp s
        JOIN gold.dim_type_indicateur_dp t ON s.code_indicateur = t.code_indicateur
        WHERE s.id_province = %(p)s
    """
    params = {'p': id_province}
    if id_centre:
        query += " AND s.id_centre = %(c)s"
        params['c'] = id_centre
    query += f" ORDER BY s.date_saisie DESC LIMIT {limit}"
    return pd.read_sql(query, engine, params=params)