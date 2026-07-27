"""
Résolution des Surrogate Keys (SK) depuis les dimensions du DWH.
Met en cache les mappings pour éviter des requêtes répétées.
"""
import hashlib
import unicodedata
import re
from functools import lru_cache
import pandas as pd
from etl.common.db import read_sql, execute
from etl.common.logger import get_logger

# Centre sentinelle pour les agrégations DP (pattern "Unknown Member")
CENTRE_AGREG_DP_ID = 0
CENTRE_AGREG_DP_CODE = "AGREG_DP"

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════
# CACHES DES MAPPINGS
# ═══════════════════════════════════════════════════════════════

@lru_cache(maxsize=1)
def get_dp_mapping() -> dict:
    """Retourne {code_dp: id_dp}."""
    df = read_sql("SELECT id_dp, code_dp FROM dwh.dim_dp")
    return dict(zip(df["code_dp"], df["id_dp"]))


@lru_cache(maxsize=1)
def get_centre_mapping() -> dict:
    """Retourne {code_centre: id_centre}."""
    df = read_sql("SELECT id_centre, code_centre FROM dwh.dim_centre")
    return dict(zip(df["code_centre"], df["id_centre"]))


@lru_cache(maxsize=1)
def get_indicateur_mapping() -> dict:
    """Retourne {code_indicateur: id_type_indicateur}."""
    df = read_sql(
        "SELECT id_type_indicateur, code_indicateur FROM dwh.dim_type_indicateur_dp"
    )
    return dict(zip(df["code_indicateur"], df["id_type_indicateur"]))


@lru_cache(maxsize=1)
def get_reclamation_mapping() -> dict:
    """Retourne {code: id_type}."""
    df = read_sql("SELECT id_type, code FROM dwh.dim_type_reclamation")
    return dict(zip(df["code"], df["id_type"]))


def clear_cache():
    """Vide tous les caches (à appeler après un rechargement des dimensions)."""
    get_dp_mapping.cache_clear()
    get_centre_mapping.cache_clear()
    get_indicateur_mapping.cache_clear()
    get_reclamation_mapping.cache_clear()
    logger.debug("🔄 Cache des mappings de dimensions vidé")


# ═══════════════════════════════════════════════════════════════
# UTILITAIRES DATE
# ═══════════════════════════════════════════════════════════════

def date_to_id_temps(date_value) -> int:
    """
    Convertit une date en id_temps (format YYYYMMDD).
    Ex: 2025-01-01 → 20250101
    """
    d = pd.to_datetime(date_value)
    return int(d.strftime("%Y%m%d"))


def year_month_to_id_temps(annee: int, mois: int) -> int:
    """
    Convertit (annee, mois) en id_temps du 1er du mois.
    Ex: (2025, 1) → 20250101
    """
    return int(f"{annee:04d}{mois:02d}01")


# ═══════════════════════════════════════════════════════════════
# GESTION DES RÉCLAMATIONS PERSONNALISÉES (STREAMLIT)
# ═══════════════════════════════════════════════════════════════

def normalize_libelle(libelle: str) -> str:
    """
    Normalise un libellé pour un hash stable et cohérent.
    
    Exemples :
      'Réclamation particulière #1'  → 'reclamation particuliere 1'
      'RECLAMATION Particulière n°1' → 'reclamation particuliere n 1'
      'autre_recl'                    → 'autre recl'
      'Fuite compteur cassé'         → 'fuite compteur casse'
    """
    if not libelle:
        return ""
    # Retirer les accents
    text = unicodedata.normalize("NFD", str(libelle))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    # Lowercase + trim
    text = text.lower().strip()
    # Retirer ponctuation et caractères spéciaux (garder lettres/chiffres/espaces)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    # Normaliser les espaces multiples
    text = re.sub(r"\s+", " ", text).strip()
    return text


def generate_custom_code(libelle: str) -> str:
    """
    Génère un code stable et déterministe pour une réclamation personnalisée.
    Le même libellé (après normalisation) produira toujours le même code.
    
    Ex: 'Réclamation particulière #1' → 'CUSTOM_A1B2C3D4'
    """
    normalized = normalize_libelle(libelle)
    if not normalized:
        raise ValueError("Libellé vide ou invalide pour la génération de code personnalisé")
    hash_short = hashlib.md5(normalized.encode("utf-8")).hexdigest()[:8].upper()
    return f"CUSTOM_{hash_short}"


def get_or_create_reclamation_id(
    libelle: str,
    categorie: str = "Reclamation_Divers",
) -> int:
    """
    Retourne l'id_type d'une réclamation personnalisée.
    - Si le libellé existe déjà (via son hash) → retourne l'id existant
    - Sinon → insère une nouvelle entrée dans DIM_TYPE_RECLAMATION et retourne son id
    
    Idempotent grâce au hash déterministe basé sur le libellé normalisé.
    Sécurisé pour l'exécution concurrente grâce à ON CONFLICT DO NOTHING.
    """
    custom_code = generate_custom_code(libelle)

    # 1. Cache
    mapping = get_reclamation_mapping()
    if custom_code in mapping:
        return mapping[custom_code]

    # 2. Vérif en base (le cache peut être obsolète)
    df = read_sql(
        "SELECT id_type FROM dwh.dim_type_reclamation WHERE code = :code",
        params={"code": custom_code},
    )
    if not df.empty:
        return int(df.iloc[0]["id_type"])

    # 3. Insertion (idempotent grâce à ON CONFLICT)
    execute(
        """
        INSERT INTO dwh.dim_type_reclamation (code, libelle, categorie, est_personnalisee)
        VALUES (:code, :libelle, :categorie, TRUE)
        ON CONFLICT (code) DO NOTHING
        """,
        params={
            "code": custom_code,
            "libelle": libelle.strip(),
            "categorie": categorie,
        },
    )
    logger.info(f"➕ Nouvelle réclamation personnalisée créée : {custom_code} → '{libelle}'")

    # 4. Récupérer l'id + rafraîchir le cache
    clear_cache()
    df = read_sql(
        "SELECT id_type FROM dwh.dim_type_reclamation WHERE code = :code",
        params={"code": custom_code},
    )
    return int(df.iloc[0]["id_type"])


def resolve_reclamation_id(code: str, libelle: str, categorie: str) -> int:
    """
    Fonction unifiée de résolution d'ID pour une réclamation.
    
    Règle métier :
    - Si categorie == 'Reclamation_Divers' → traiter comme personnalisée (hash du libellé)
      (le code Streamlit type 'DIVERS_CUSTOM_N' est ignoré car non sémantique)
    - Sinon → utiliser le code standard (FUITE_EAU, MANQUE_PRESSION, AUTRES, etc.)
    
    Cette fonction gère les 3 cas :
    1. Excel standard        (ex: code='FUITE_EAU')
    2. Excel "Autres"        (ex: code='AUTRES')
    3. Streamlit standard    (ex: code='FUITE_EAU')
    4. Streamlit personnalisé (ex: code='DIVERS_CUSTOM_1', libelle='recl1' → CUSTOM_<hash>)
    """
    # Cas personnalisé Streamlit
    if categorie == "Reclamation_Divers" and code and code.startswith("DIVERS_CUSTOM_"):
        return get_or_create_reclamation_id(libelle, categorie)

    # Cas standard (Excel ou Streamlit)
    mapping = get_reclamation_mapping()
    if code in mapping:
        return mapping[code]

    # Fallback : code inconnu mais catégorie 'Reclamation_Divers' → traiter comme custom
    if categorie == "Reclamation_Divers":
        logger.warning(f"Code '{code}' inconnu mais catégorie Divers → traitement custom via libellé '{libelle}'")
        return get_or_create_reclamation_id(libelle, categorie)

    raise ValueError(
        f"Code réclamation inconnu : '{code}' (libellé='{libelle}', catégorie='{categorie}')"
    )