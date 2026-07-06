"""
============================================================
SRM Souss-Massa - Fonctions utilitaires
============================================================
"""

from datetime import datetime


def nom_mois(mois):
    """Retourner le nom du mois en français"""
    noms = [
        'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
        'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
    ]
    if 1 <= mois <= 12:
        return noms[mois - 1]
    return str(mois)


def formatter_nombre(valeur, decimales=2):
    """Formater un nombre avec séparateur de milliers"""
    if valeur is None:
        return "-"
    try:
        return f"{valeur:,.{decimales}f}".replace(",", " ")
    except:
        return str(valeur)


def formatter_pourcentage(valeur):
    """Formater en pourcentage"""
    if valeur is None:
        return "-"
    try:
        return f"{valeur:.2f}%"
    except:
        return str(valeur)


def periode_annees(depuis=2024, jusqu_a=None):
    """Générer liste des années"""
    if jusqu_a is None:
        jusqu_a = datetime.now().year + 1
    return list(range(depuis, jusqu_a + 1))


def mois_avec_noms():
    """Retourner liste de tuples (numero, nom)"""
    return [(i, nom_mois(i)) for i in range(1, 13)]