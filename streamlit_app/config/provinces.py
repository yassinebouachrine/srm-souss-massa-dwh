# config/provinces.py
"""
Configuration des 6 provinces de la région Souss-Massa
avec tous les centres de distribution réels.
"""

PROVINCES = {
    1: {
        "code": "TATA",
        "nom": "Tata",
        "id_province": 1,
        "centres": [
            {"id": 1, "code": "C_TATA_01", "nom": "Tata", "type": "Principal"},
            {"id": 2, "code": "C_TATA_02", "nom": "Foum Zguid", "type": "Secondaire"},
            {"id": 3, "code": "C_TATA_03", "nom": "Ait Baha Mbarek", "type": "Secondaire"},
            {"id": 4, "code": "C_TATA_04", "nom": "Akka", "type": "Secondaire"},
            {"id": 5, "code": "C_TATA_05", "nom": "Foum Lhssen", "type": "Secondaire"},
            {"id": 6, "code": "C_TATA_06", "nom": "Tissent", "type": "Secondaire"},
            {"id": 7, "code": "C_TATA_07", "nom": "Allougoum", "type": "Secondaire"},
            {"id": 8, "code": "C_TATA_08", "nom": "Issafen", "type": "Secondaire"},
            {"id": 9, "code": "C_TATA_09", "nom": "Akka Ighane", "type": "Secondaire"},
            {"id": 10, "code": "C_TATA_10", "nom": "Tigzmirte", "type": "Secondaire"},
            {"id": 11, "code": "C_TATA_11", "nom": "Ait Ouabelli", "type": "Secondaire"},
            {"id": 12, "code": "C_TATA_12", "nom": "Smira - Foum Zguid", "type": "Secondaire"},
        ]
    },
    2: {
        "code": "TIZNIT",
        "nom": "Tiznit",
        "id_province": 2,
        "centres": [
            {"id": 13, "code": "C_TIZ_01", "nom": "Tiznit", "type": "Principal"},
            {"id": 14, "code": "C_TIZ_02", "nom": "Tafraout", "type": "Secondaire"},
            {"id": 15, "code": "C_TIZ_03", "nom": "Aval Tiznit", "type": "Secondaire"},
            {"id": 16, "code": "C_TIZ_04", "nom": "Amont Tiznit", "type": "Secondaire"},
            {"id": 17, "code": "C_TIZ_05", "nom": "Talaint", "type": "Secondaire"},
            {"id": 18, "code": "C_TIZ_06", "nom": "Tizoughrane", "type": "Secondaire"},
            {"id": 19, "code": "C_TIZ_07", "nom": "Douars Talaint", "type": "Secondaire"},
            {"id": 20, "code": "C_TIZ_08", "nom": "Ammelne", "type": "Secondaire"},
            {"id": 21, "code": "C_TIZ_09", "nom": "Larbaa Sahel", "type": "Secondaire"},
            {"id": 22, "code": "C_TIZ_10", "nom": "Aglou", "type": "Secondaire"},
            {"id": 23, "code": "C_TIZ_11", "nom": "Tighmi", "type": "Secondaire"},
            {"id": 24, "code": "C_TIZ_12", "nom": "Zaouia", "type": "Secondaire"},
            {"id": 25, "code": "C_TIZ_13", "nom": "Lmaadar Lakbir", "type": "Secondaire"},
            {"id": 26, "code": "C_TIZ_14", "nom": "Anzi", "type": "Secondaire"},
            {"id": 27, "code": "C_TIZ_15", "nom": "Ras Mouka", "type": "Secondaire"},
        ]
    },
    3: {
        "code": "CHTOUKA",
        "nom": "Chtouka Ait Baha",
        "id_province": 3,
        "centres": [
            {"id": 28, "code": "C_CHT_01", "nom": "Biougra", "type": "Principal"},
            {"id": 29, "code": "C_CHT_02", "nom": "Sidi Bibi", "type": "Secondaire"},
            {"id": 30, "code": "C_CHT_03", "nom": "Massa Douars", "type": "Secondaire"},
            {"id": 31, "code": "C_CHT_04", "nom": "Massa", "type": "Secondaire"},
            {"id": 32, "code": "C_CHT_05", "nom": "Ait Baha", "type": "Secondaire"},
            {"id": 33, "code": "C_CHT_06", "nom": "Ait Baha Douars", "type": "Secondaire"},
            {"id": 34, "code": "C_CHT_07", "nom": "Belfaa et Douars", "type": "Secondaire"},
            {"id": 35, "code": "C_CHT_08", "nom": "Ait Milk", "type": "Secondaire"},
            {"id": 36, "code": "C_CHT_09", "nom": "Ait Milk Douars", "type": "Secondaire"},
            {"id": 37, "code": "C_CHT_10", "nom": "Idaougnidif", "type": "Secondaire"},
            {"id": 38, "code": "C_CHT_11", "nom": "Douira", "type": "Secondaire"},
            {"id": 39, "code": "C_CHT_12", "nom": "Inchaden", "type": "Secondaire"},
            {"id": 40, "code": "C_CHT_13", "nom": "Ait Aamira", "type": "Secondaire"},
        ]
    },
    4: {
        "code": "TAROUDANT",
        "nom": "Taroudant",
        "id_province": 4,
        "centres": [
            {"id": 41, "code": "C_TAR_01", "nom": "Taroudant", "type": "Principal"},
            {"id": 42, "code": "C_TAR_02", "nom": "Ouled Teima", "type": "Secondaire"},
            {"id": 43, "code": "C_TAR_03", "nom": "Ouled Berhil", "type": "Secondaire"},
            {"id": 44, "code": "C_TAR_04", "nom": "Ait Iaaza", "type": "Secondaire"},
            {"id": 45, "code": "C_TAR_05", "nom": "Taliouine", "type": "Secondaire"},
            {"id": 46, "code": "C_TAR_06", "nom": "Laglalcha", "type": "Secondaire"},
            {"id": 47, "code": "C_TAR_07", "nom": "Aoulouz", "type": "Secondaire"},
            {"id": 48, "code": "C_TAR_08", "nom": "Sidi El Guerdan", "type": "Secondaire"},
            {"id": 49, "code": "C_TAR_09", "nom": "Sidi Mohamed Lhamri", "type": "Secondaire"},
            {"id": 50, "code": "C_TAR_10", "nom": "Ighrem", "type": "Secondaire"},
            {"id": 51, "code": "C_TAR_11", "nom": "Ait Addellah", "type": "Secondaire"},
        ]
    },
    5: {
        "code": "INEZGANE",
        "nom": "Inezgane Ait Melloul",
        "id_province": 5,
        "centres": [
            {"id": 52, "code": "C_INZ_01", "nom": "Lqliaa", "type": "Principal"},
            {"id": 53, "code": "C_INZ_02", "nom": "Temsia", "type": "Secondaire"},
            {"id": 54, "code": "C_INZ_03", "nom": "Ouled Dahhou", "type": "Secondaire"},
        ]
    },
    6: {
        "code": "AGADIR",
        "nom": "Agadir",
        "id_province": 6,
        "centres": [
            {"id": 55, "code": "C_AGA_01", "nom": "Agadir (Ex-RAMSA)", "type": "Principal"},
            {"id": 56, "code": "C_AGA_02", "nom": "Drarga", "type": "Secondaire"},
            {"id": 57, "code": "C_AGA_03", "nom": "Douars Drarga (Tamait)", "type": "Secondaire"},
            {"id": 58, "code": "C_AGA_04", "nom": "Amskroud", "type": "Secondaire"},
            {"id": 59, "code": "C_AGA_05", "nom": "Douars Amskroud", "type": "Secondaire"},
            {"id": 60, "code": "C_AGA_06", "nom": "Douars Taghazout", "type": "Secondaire"},
            {"id": 61, "code": "C_AGA_07", "nom": "Taghazout", "type": "Secondaire"},
            {"id": 62, "code": "C_AGA_08", "nom": "Douars Immouzer", "type": "Secondaire"},
            {"id": 63, "code": "C_AGA_09", "nom": "Immouzer", "type": "Secondaire"},
            {"id": 64, "code": "C_AGA_10", "nom": "Tamri", "type": "Secondaire"},
            {"id": 65, "code": "C_AGA_11", "nom": "Douars Tamri", "type": "Secondaire"},
            {"id": 66, "code": "C_AGA_12", "nom": "Douars Imsouane", "type": "Secondaire"},
            {"id": 67, "code": "C_AGA_13", "nom": "Imsouane", "type": "Secondaire"},
            {"id": 68, "code": "C_AGA_14", "nom": "Aziar", "type": "Secondaire"},
        ]
    },
}


def get_province_by_code(code: str):
    """Retourne la province correspondant au code donné."""
    for pid, prov in PROVINCES.items():
        if prov["code"] == code:
            return prov
    return None


def get_province_name(id_province: int) -> str:
    """Retourne le nom d'une province par son ID."""
    return PROVINCES.get(id_province, {}).get("nom", "Inconnu")


def get_all_province_names() -> list:
    """Retourne la liste de tous les noms de provinces."""
    return [p["nom"] for p in PROVINCES.values()]


def get_centres_for_province(id_province: int) -> list:
    """Retourne la liste des centres pour une province donnée."""
    return PROVINCES.get(id_province, {}).get("centres", [])


def get_all_centres() -> list:
    """Retourne tous les centres de toutes les provinces."""
    all_centres = []
    for pid, prov in PROVINCES.items():
        for centre in prov["centres"]:
            all_centres.append({
                **centre,
                "id_province": pid,
                "province": prov["nom"],
                "code_province": prov["code"],
            })
    return all_centres


def get_province_id_by_centre(id_centre: int) -> int:
    """Retourne l'ID de la province à laquelle appartient un centre."""
    for pid, prov in PROVINCES.items():
        for centre in prov["centres"]:
            if centre["id"] == id_centre:
                return pid
    return None


def get_centre_by_id(id_centre: int) -> dict:
    """Retourne les infos d'un centre par son ID."""
    for pid, prov in PROVINCES.items():
        for centre in prov["centres"]:
            if centre["id"] == id_centre:
                return {**centre, "id_province": pid, "province": prov["nom"]}
    return None