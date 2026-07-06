"""
============================================================
SRM Souss-Massa - Validation métier
============================================================
"""


def valider_rendement(valeur):
    """Rendement doit être entre 0 et 100%"""
    if valeur is None:
        return True, ""
    if 0 <= valeur <= 100:
        return True, ""
    return False, "Le rendement doit être entre 0 et 100%"


def valider_ilp(valeur):
    """ILP doit être positif"""
    if valeur is None:
        return True, ""
    if valeur >= 0:
        return True, ""
    return False, "L'ILP doit être positif"


def valider_volume(valeur):
    """Volume doit être positif"""
    if valeur is None:
        return True, ""
    if valeur >= 0:
        return True, ""
    return False, "Le volume doit être positif"


def valider_nombre_positif(valeur, nom_champ="valeur"):
    """Nombre entier positif"""
    if valeur is None:
        return True, ""
    if valeur >= 0:
        return True, ""
    return False, f"Le {nom_champ} doit être positif"


def valider_indicateur(code_indicateur, valeur):
    """Valider un indicateur selon son code"""
    validations = {
        'REND': valider_rendement,
        'ILP': valider_ilp,
        'ACHAT': valider_volume,
        'VENTE': valider_volume,
        'AUTOPROD': valider_volume,
        'CESSION': valider_volume,
        'VOL_FRAUD': valider_volume,
    }
    
    validator = validations.get(code_indicateur, valider_nombre_positif)
    return validator(valeur)


def valider_annee_mois(annee, mois):
    """Valider année et mois"""
    if annee < 2020 or annee > 2050:
        return False, "L'année doit être entre 2020 et 2050"
    if mois < 1 or mois > 12:
        return False, "Le mois doit être entre 1 et 12"
    return True, ""