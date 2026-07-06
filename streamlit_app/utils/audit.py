"""
============================================================
SRM Souss-Massa - Audit des actions
============================================================
"""

import json
from streamlit_app.db.connection import get_db_connection


def log_action(utilisateur, action, table_cible, id_enregistrement, 
               donnees_avant=None, donnees_apres=None):
    """
    Enregistrer une action dans audit.log_saisies
    
    Args:
        utilisateur: nom d'utilisateur
        action: INSERT, UPDATE, DELETE, VALIDATE, REJECT
        table_cible: nom de la table modifiée
        id_enregistrement: ID de la ligne modifiée
        donnees_avant: dict des données avant modif (optionnel)
        donnees_apres: dict des données après modif (optionnel)
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO audit.log_saisies
                    (utilisateur, action, table_cible, id_enregistrement,
                     donnees_avant, donnees_apres)
                VALUES 
                    (%s, %s, %s, %s, %s, %s)
            """, (
                utilisateur,
                action,
                table_cible,
                id_enregistrement,
                json.dumps(donnees_avant) if donnees_avant else None,
                json.dumps(donnees_apres) if donnees_apres else None
            ))
            conn.commit()
    except Exception as e:
        print(f"Erreur audit: {e}")


def get_recent_actions(utilisateur=None, limit=100):
    """Récupérer les actions récentes"""
    import pandas as pd
    from streamlit_app.db.connection import get_engine
    
    engine = get_engine()
    
    if utilisateur:
        query = """
            SELECT utilisateur, action, table_cible, id_enregistrement, date_action
            FROM audit.log_saisies
            WHERE utilisateur = %(utilisateur)s
            ORDER BY date_action DESC
            LIMIT %(limit)s
        """
        return pd.read_sql(query, engine, params={
            'utilisateur': utilisateur,
            'limit': limit
        })
    else:
        query = """
            SELECT utilisateur, action, table_cible, id_enregistrement, date_action
            FROM audit.log_saisies
            ORDER BY date_action DESC
            LIMIT %(limit)s
        """
        return pd.read_sql(query, engine, params={'limit': limit})