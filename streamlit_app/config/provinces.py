# config/provinces.py

PROVINCES = {
    1: {
        "code": "TATA",
        "nom": "Tata",
        "id_province": 1,
        "centres": [
            {"id": 1, "code": "C_TATA_01", "nom": "Centre Tata Ville", "type": "Principal"},
            {"id": 2, "code": "C_TATA_02", "nom": "Centre Akka", "type": "Secondaire"},
            {"id": 3, "code": "C_TATA_03", "nom": "Centre Foum Zguid", "type": "Secondaire"},
        ]
    },
    2: {
        "code": "TIZNIT",
        "nom": "Tiznit",
        "id_province": 2,
        "centres": [
            {"id": 4, "code": "C_TIZ_01", "nom": "Centre Tiznit Ville", "type": "Principal"},
            {"id": 5, "code": "C_TIZ_02", "nom": "Centre Aglou", "type": "Secondaire"},
            {"id": 6, "code": "C_TIZ_03", "nom": "Centre Sidi Ifni", "type": "Secondaire"},
        ]
    },
    3: {
        "code": "CHTOUKA",
        "nom": "Chtouka Ait Baha",
        "id_province": 3,
        "centres": [
            {"id": 7, "code": "C_CHT_01", "nom": "Centre Biougra", "type": "Principal"},
            {"id": 8, "code": "C_CHT_02", "nom": "Centre Ait Baha", "type": "Secondaire"},
        ]
    },
    4: {
        "code": "TAROUDANT",
        "nom": "Taroudant",
        "id_province": 4,
        "centres": [
            {"id": 9, "code": "C_TAR_01", "nom": "Centre Taroudant Ville", "type": "Principal"},
            {"id": 10, "code": "C_TAR_02", "nom": "Centre Ouled Teima", "type": "Secondaire"},
            {"id": 11, "code": "C_TAR_03", "nom": "Centre Taliouine", "type": "Secondaire"},
            {"id": 12, "code": "C_TAR_04", "nom": "Centre Oulad Berhil", "type": "Secondaire"},
        ]
    },
    5: {
        "code": "INEZGANE",
        "nom": "Inezgane Ait Melloul",
        "id_province": 5,
        "centres": [
            {"id": 13, "code": "C_INZ_01", "nom": "Centre Inezgane", "type": "Principal"},
            {"id": 14, "code": "C_INZ_02", "nom": "Centre Ait Melloul", "type": "Secondaire"},
            {"id": 15, "code": "C_INZ_03", "nom": "Centre Dcheira", "type": "Secondaire"},
        ]
    },
    6: {
        "code": "AGADIR",
        "nom": "Agadir (Siège)",
        "id_province": 6,
        "centres": [
            {"id": 16, "code": "C_AGA_01", "nom": "Centre Agadir Ville", "type": "Principal"},
            {"id": 17, "code": "C_AGA_02", "nom": "Centre Aourir", "type": "Secondaire"},
            {"id": 18, "code": "C_AGA_03", "nom": "Centre Drarga", "type": "Secondaire"},
        ]
    },
}

def get_province_by_code(code: str):
    for pid, prov in PROVINCES.items():
        if prov["code"] == code:
            return prov
    return None

def get_province_name(id_province: int) -> str:
    return PROVINCES.get(id_province, {}).get("nom", "Inconnu")

def get_all_province_names() -> list:
    return [p["nom"] for p in PROVINCES.values()]

def get_centres_for_province(id_province: int) -> list:
    return PROVINCES.get(id_province, {}).get("centres", [])