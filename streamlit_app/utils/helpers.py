# utils/helpers.py
from datetime import datetime
import uuid
import pandas as pd


MOIS_FR = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre",
}


def generate_lot_id(province_code: str, data_type: str) -> str:
    """Génère un identifiant unique pour un lot de saisie."""
    now = datetime.now()
    short_uuid = uuid.uuid4().hex[:8].upper()
    return f"{province_code}_{data_type}_{now.strftime('%Y%m%d_%H%M%S')}_{short_uuid}"


def get_current_period():
    """Retourne (année, mois) courants."""
    now = datetime.now()
    return now.year, now.month


def format_datetime(dt) -> str:
    """
    Formate une datetime en string.
    Gère les valeurs NULL, NaT, None, et pandas Timestamps.
    """
    if dt is None:
        return "—"

    # Gérer pandas NaT
    try:
        if pd.isna(dt):
            return "—"
    except (TypeError, ValueError):
        pass

    # Gérer les strings
    if isinstance(dt, str):
        if not dt.strip():
            return "—"
        try:
            dt = pd.to_datetime(dt)
        except:
            return dt

    # Formater
    try:
        return dt.strftime("%d/%m/%Y à %H:%M")
    except (AttributeError, ValueError):
        return "—"


def format_date(dt) -> str:
    """Formate une date sans l'heure."""
    if dt is None:
        return "—"
    try:
        if pd.isna(dt):
            return "—"
    except (TypeError, ValueError):
        pass
    try:
        return dt.strftime("%d/%m/%Y")
    except (AttributeError, ValueError):
        return "—"


def get_mois_name(mois: int) -> str:
    """Retourne le nom du mois."""
    if mois is None:
        return "—"
    return MOIS_FR.get(mois, str(mois))