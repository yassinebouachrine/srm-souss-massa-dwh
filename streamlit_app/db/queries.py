"""
============================================================
SRM Souss-Massa - Requêtes SQL
============================================================
"""

import pandas as pd
from streamlit_app.db.connection import get_engine, get_db_connection


# ============================================================
# LECTURES (Dimensions)
# ============================================================

def get_provinces():
    """Récupérer toutes les provinces"""
    engine = get_engine()
    query = """
        SELECT id_province, code_province, nom_province
        FROM gold.dim_province
        ORDER BY nom_province
    """
    return pd.read_sql(query, engine)


def get_centres(id_province=None):
    """Récupérer les centres (optionnellement filtrés par province)"""
    engine = get_engine()
    if id_province:
        query = """
            SELECT id_centre, code_centre, nom_centre, type_centre
            FROM gold.dim_centre
            WHERE id_province = %(id_province)s
            ORDER BY nom_centre
        """
        return pd.read_sql(query, engine, params={'id_province': id_province})
    else:
        query = """
            SELECT id_centre, code_centre, nom_centre, type_centre, id_province
            FROM gold.dim_centre
            ORDER BY nom_centre
        """
        return pd.read_sql(query, engine)


def get_types_indicateurs():
    """Récupérer les 21 types d'indicateurs"""
    engine = get_engine()
    query = """
        SELECT id_type_indicateur, code_indicateur, libelle_indicateur,
               unite, categorie, sous_categorie, ordre_affichage
        FROM gold.dim_type_indicateur_dp
        ORDER BY ordre_affichage
    """
    return pd.read_sql(query, engine)


def get_types_reclamations():
    """Récupérer les 10 types de réclamations"""
    engine = get_engine()
    query = """
        SELECT id_type_reclamation, code_type, libelle_reclamation,
               categorie_reclamation, est_comptage, est_duree, ordre_affichage
        FROM gold.dim_type_reclamation
        ORDER BY ordre_affichage
    """
    return pd.read_sql(query, engine)


def get_etages():
    """Récupérer les étages de pression"""
    engine = get_engine()
    query = """
        SELECT id_etage, code_etage, nom_etage, cote_pression, 
               lineaire_km, id_province, id_centre
        FROM gold.dim_etage_pression
        ORDER BY nom_etage
    """
    return pd.read_sql(query, engine)


# ============================================================
# INSERTIONS STAGING
# ============================================================

def insert_indicateur_dp(data):
    """Insérer un indicateur DP dans staging"""
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
    """Insérer une réclamation dans staging"""
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
                commentaire = EXCLUDED.commentaire,
                statut = EXCLUDED.statut,
                modifie_par = EXCLUDED.saisi_par,
                date_modification = NOW()
            RETURNING id_saisie, (xmax = 0) AS inserted
        """, data)
        result = cur.fetchone()
        conn.commit()
        return result['id_saisie'], result['inserted']


def insert_rendement_etage(data):
    """Insérer un rendement d'étage"""
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
                commentaire = EXCLUDED.commentaire,
                statut = EXCLUDED.statut,
                modifie_par = EXCLUDED.saisi_par,
                date_modification = NOW()
            RETURNING id_saisie, (xmax = 0) AS inserted
        """, data)
        result = cur.fetchone()
        conn.commit()
        return result['id_saisie'], result['inserted']


# ============================================================
# CONSULTATION
# ============================================================

def get_indicateurs_saisis(id_province, id_centre, annee, mois):
    """Récupérer les indicateurs déjà saisis pour un contexte"""
    engine = get_engine()
    query = """
        SELECT code_indicateur, valeur, statut
        FROM staging.indicateurs_dp
        WHERE id_province = %(id_province)s
          AND (id_centre = %(id_centre)s OR (id_centre IS NULL AND %(id_centre)s IS NULL))
          AND annee = %(annee)s
          AND mois = %(mois)s
    """
    df = pd.read_sql(query, engine, params={
        'id_province': id_province,
        'id_centre': id_centre,
        'annee': annee,
        'mois': mois
    })
    return dict(zip(df['code_indicateur'], df['valeur']))


def get_historique_saisies(id_province, id_centre=None, limit=50):
    """Récupérer l'historique des saisies"""
    engine = get_engine()
    query = """
        SELECT 
            s.annee, s.mois, 
            t.libelle_indicateur AS indicateur,
            t.unite,
            s.valeur, s.statut,
            s.saisi_par, s.date_saisie,
            CASE WHEN s.est_traite THEN 'Integre' ELSE 'En attente' END AS traitement
        FROM staging.indicateurs_dp s
        JOIN gold.dim_type_indicateur_dp t ON s.code_indicateur = t.code_indicateur
        WHERE s.id_province = %(id_province)s
    """
    params = {'id_province': id_province}
    
    if id_centre:
        query += " AND s.id_centre = %(id_centre)s"
        params['id_centre'] = id_centre
    
    query += f" ORDER BY s.date_saisie DESC LIMIT {limit}"
    
    return pd.read_sql(query, engine, params=params)