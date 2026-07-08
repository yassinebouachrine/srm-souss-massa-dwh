# utils/helpers.py
from datetime import datetime
import uuid

MOIS_FR = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre",
}

MOIS_FR_SHORT = {
    1: "Jan", 2: "Fév", 3: "Mar", 4: "Avr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Aoû", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Déc",
}


def generate_lot_id(province_code: str, data_type: str) -> str:
    now = datetime.now()
    short_uuid = uuid.uuid4().hex[:8].upper()
    return f"{province_code}_{data_type}_{now.strftime('%Y%m%d_%H%M%S')}_{short_uuid}"


def get_current_period():
    now = datetime.now()
    return now.year, now.month


def format_datetime(dt) -> str:
    if dt:
        return dt.strftime("%d/%m/%Y à %H:%M")
    return "—"


def format_date(dt) -> str:
    if dt:
        return dt.strftime("%d/%m/%Y")
    return "—"


def get_mois_name(mois: int) -> str:
    return MOIS_FR.get(mois, str(mois))