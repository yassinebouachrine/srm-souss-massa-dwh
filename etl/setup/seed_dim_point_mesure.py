"""
Seed DIM_POINT_MESURE depuis le référentiel Excel PMAC.

Lit le fichier : data/raw/referentiels/Liste des points de mesure 9_12_2025.xlsx
Peuple : dwh.dim_point_mesure (avec id_source_mesure = PMAC_LIVE)

Ce script est IDEMPOTENT :
  - INSERT ... ON CONFLICT (id_pmac) DO UPDATE
  - Peut être relancé sans doublons

Exécution :
    python -m etl.setup.seed_dim_point_mesure
"""
from pathlib import Path
import pandas as pd
import unicodedata
from sqlalchemy import text

from etl.common.config import get_path
from etl.common.db import get_engine, read_sql
from etl.common.logger import get_logger

logger = get_logger(__name__)

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

REFERENTIEL_FILENAME = "Liste des points de mesure 9_12_2025.xlsx"
SHEET_NAME = "Feuil1"

# Mapping colonnes Excel → colonnes SQL
COLUMN_MAPPING = {
    "Id PMAC":                  "id_pmac_raw",
    "Point de mesure":          "nom_point",
    "Longitude":                "longitude",
    "Latitude":                 "latitude",
    "Secteur":                  "secteur_source",       # Info seulement (pas dans dim_point_mesure)
    "Groupes Pts Mesure":       "groupe_mesure",
    "Est Modulateur":           "est_modulateur",
    "Est points de pression":   "est_pression",
    "Est Debit":                "est_debit",
    "Est Gros Conso":           "est_gros_conso_src",   # Info seulement
    "Est Reservoir":            "est_reservoir",
}


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _normalize_bool(v) -> bool:
    """Convertit 'Oui'/'oui'/'OUI'/True → True, sinon False."""
    if pd.isna(v):
        return False
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() == "oui"


def _pad_pmac_id(v) -> str:
    """
    Convertit un Id PMAC en id_pmac 4 chiffres.
    Ex: 7 → "0007", 416 → "0416"
    """
    if pd.isna(v):
        return None
    return str(int(v)).zfill(4)


def _clean_string(v) -> str:
    """Nettoie une chaîne : trim + remplace NaN par None."""
    if pd.isna(v):
        return None
    s = str(v).strip()
    return s if s else None


def _clean_float(v):
    """Convertit en float en gérant les espaces et virgules."""
    if pd.isna(v):
        return None
    try:
        s = str(v).strip().replace(",", ".")
        return float(s)
    except (ValueError, TypeError):
        return None


# ═══════════════════════════════════════════════════════════════
# LECTURE DU RÉFÉRENTIEL
# ═══════════════════════════════════════════════════════════════

def load_referentiel_excel() -> pd.DataFrame:
    """Charge le fichier Excel référentiel PMAC."""
    filepath = get_path("raw") / "referentiels" / REFERENTIEL_FILENAME
    
    if not filepath.exists():
        raise FileNotFoundError(
            f"❌ Fichier référentiel introuvable : {filepath}\n"
            f"   Placez le fichier dans : data/raw/referentiels/"
        )
    
    logger.info(f"📖 Lecture référentiel : {filepath.name}")
    
    # Lecture avec header sur la 1ère ligne
    df = pd.read_excel(filepath, sheet_name=SHEET_NAME, engine="openpyxl")
    
    logger.info(f"   → {len(df)} lignes brutes, colonnes : {list(df.columns)}")
    
    return df


def transform_referentiel(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Transforme le DataFrame brut en format DB-ready.
    Filtre les lignes invalides.
    """
    logger.info("🔄 Transformation référentiel...")
    
    # 1. Sélectionner uniquement les colonnes qui existent
    cols_present = [c for c in COLUMN_MAPPING.keys() if c in df_raw.columns]
    df = df_raw[cols_present].copy()
    df.columns = [COLUMN_MAPPING[c] for c in cols_present]
    
    # 2. Nettoyer chaque colonne
    df["id_pmac"] = df["id_pmac_raw"].apply(_pad_pmac_id)
    
    if "nom_point" in df.columns:
        df["nom_point"] = df["nom_point"].apply(_clean_string)
    if "groupe_mesure" in df.columns:
        df["groupe_mesure"] = df["groupe_mesure"].apply(_clean_string)
    
    if "longitude" in df.columns:
        df["longitude"] = df["longitude"].apply(_clean_float)
    if "latitude" in df.columns:
        df["latitude"] = df["latitude"].apply(_clean_float)
    
    # Flags booléens
    for col in ["est_modulateur", "est_pression", "est_debit", "est_reservoir"]:
        if col in df.columns:
            df[col] = df[col].apply(_normalize_bool)
        else:
            df[col] = False
    
    # est_gros_conso (info source, pas stocké mais utilisé pour logging)
    if "est_gros_conso_src" in df.columns:
        df["est_gros_conso"] = df["est_gros_conso_src"].apply(_normalize_bool)
    else:
        df["est_gros_conso"] = False
    
    # est_amont / est_aval : déduits du groupe_mesure ou du nom
    df["est_amont"] = False
    df["est_aval"]  = False
    # Détection basique via mots-clés dans nom_point
    if "nom_point" in df.columns:
        df.loc[df["nom_point"].str.contains("amont|Amont|AMONT", na=False, regex=True), "est_amont"] = True
        df.loc[df["nom_point"].str.contains("aval|Aval|AVAL",    na=False, regex=True), "est_aval"]  = True
    
    # 3. Filtrer les lignes invalides
    nb_avant = len(df)
    df = df[df["id_pmac"].notna()]
    df = df[df["nom_point"].notna()]
    nb_apres = len(df)
    
    logger.info(f"   ✅ {nb_apres} points valides ({nb_avant - nb_apres} lignes filtrées)")
    
    # 4. Détection doublons id_pmac
    duplicates = df[df["id_pmac"].duplicated(keep=False)]
    if not duplicates.empty:
        logger.warning(f"   ⚠️  {len(duplicates)} doublons id_pmac détectés :")
        for pmac_id in duplicates["id_pmac"].unique():
            noms = df[df["id_pmac"] == pmac_id]["nom_point"].tolist()
            logger.warning(f"      • {pmac_id} : {noms}")
        # On garde le premier
        df = df.drop_duplicates(subset=["id_pmac"], keep="first")
        logger.warning(f"   → Conservation du premier de chaque doublon")
    
    return df


# ═══════════════════════════════════════════════════════════════
# CHARGEMENT EN BASE
# ═══════════════════════════════════════════════════════════════

UPSERT_SQL = """
INSERT INTO dwh.dim_point_mesure (
    id_pmac, id_source_mesure, nom_point, groupe_mesure,
    latitude, longitude,
    est_pression, est_debit, est_reservoir, est_modulateur,
    est_amont, est_aval,
    fichier_source_ref, est_actif, date_modification
) VALUES (
    :id_pmac, :id_source_mesure, :nom_point, :groupe_mesure,
    :latitude, :longitude,
    :est_pression, :est_debit, :est_reservoir, :est_modulateur,
    :est_amont, :est_aval,
    :fichier_source_ref, TRUE, CURRENT_TIMESTAMP
)
ON CONFLICT (id_pmac) DO UPDATE SET
    nom_point           = EXCLUDED.nom_point,
    groupe_mesure       = EXCLUDED.groupe_mesure,
    latitude            = EXCLUDED.latitude,
    longitude           = EXCLUDED.longitude,
    est_pression        = EXCLUDED.est_pression,
    est_debit           = EXCLUDED.est_debit,
    est_reservoir       = EXCLUDED.est_reservoir,
    est_modulateur      = EXCLUDED.est_modulateur,
    est_amont           = EXCLUDED.est_amont,
    est_aval            = EXCLUDED.est_aval,
    fichier_source_ref  = EXCLUDED.fichier_source_ref,
    date_modification   = CURRENT_TIMESTAMP;
"""


def get_source_mesure_id(code_source: str = "PMAC_LIVE") -> int:
    """Récupère l'id_source_mesure de PMAC_LIVE."""
    df = read_sql(
        "SELECT id_source_mesure FROM dwh.dim_source_mesure WHERE code_source = :code",
        params={"code": code_source}
    )
    if df.empty:
        raise ValueError(f"❌ Source '{code_source}' introuvable dans dim_source_mesure. "
                         f"Exécutez d'abord 14_seed_dwh_source_mesure.sql")
    return int(df.iloc[0]["id_source_mesure"])


def load_to_dwh(df: pd.DataFrame, id_source_mesure: int) -> int:
    """Charge le DataFrame dans dwh.dim_point_mesure via UPSERT."""
    logger.info(f"📥 Chargement dans dwh.dim_point_mesure ({len(df)} lignes)...")
    
    records = [
        {
            "id_pmac":            row["id_pmac"],
            "id_source_mesure":   id_source_mesure,
            "nom_point":          row["nom_point"],
            "groupe_mesure":      row.get("groupe_mesure"),
            "latitude":           row.get("latitude"),
            "longitude":          row.get("longitude"),
            "est_pression":       bool(row.get("est_pression", False)),
            "est_debit":          bool(row.get("est_debit", False)),
            "est_reservoir":      bool(row.get("est_reservoir", False)),
            "est_modulateur":     bool(row.get("est_modulateur", False)),
            "est_amont":          bool(row.get("est_amont", False)),
            "est_aval":           bool(row.get("est_aval", False)),
            "fichier_source_ref": REFERENTIEL_FILENAME,
        }
        for _, row in df.iterrows()
    ]
    
    engine = get_engine()
    stmt = text(UPSERT_SQL)
    total = 0
    BATCH = 100
    
    with engine.begin() as conn:
        for i in range(0, len(records), BATCH):
            batch = records[i:i + BATCH]
            conn.execute(stmt, batch)
            total += len(batch)
    
    logger.info(f"✅ {total} points UPSERT dans dwh.dim_point_mesure")
    return total


# ═══════════════════════════════════════════════════════════════
# VÉRIFICATIONS APRÈS CHARGEMENT
# ═══════════════════════════════════════════════════════════════

def print_summary():
    """Affiche un résumé après le chargement."""
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DIM_POINT_MESURE")
    print("=" * 70)
    
    df = read_sql("""
        SELECT 
            COUNT(*) AS nb_total,
            COUNT(*) FILTER (WHERE est_pression)   AS nb_pression,
            COUNT(*) FILTER (WHERE est_debit)      AS nb_debit,
            COUNT(*) FILTER (WHERE est_reservoir)  AS nb_reservoir,
            COUNT(*) FILTER (WHERE est_modulateur) AS nb_modulateur,
            COUNT(*) FILTER (WHERE latitude IS NULL OR longitude IS NULL) AS nb_sans_gps
        FROM dwh.dim_point_mesure
        WHERE id_source_mesure = (
            SELECT id_source_mesure FROM dwh.dim_source_mesure WHERE code_source = 'PMAC_LIVE'
        );
    """)
    print(df.to_string(index=False))
    
    print("\n📊 RÉPARTITION PAR GROUPE_MESURE :")
    df = read_sql("""
        SELECT groupe_mesure, COUNT(*) AS nb
        FROM dwh.dim_point_mesure
        GROUP BY groupe_mesure
        ORDER BY nb DESC;
    """)
    print(df.to_string(index=False))
    
    print("\n📊 ÉCHANTILLON (10 premiers) :")
    df = read_sql("""
        SELECT id_pmac, nom_point, groupe_mesure, 
               est_pression, est_debit, est_reservoir, est_modulateur
        FROM dwh.dim_point_mesure
        ORDER BY id_pmac
        LIMIT 10;
    """)
    print(df.to_string(index=False))
    print("=" * 70)


# ═══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def main():
    logger.info("=" * 70)
    logger.info("🌱 SEED DIM_POINT_MESURE (depuis référentiel Excel)")
    logger.info("=" * 70)
    
    # 1. Récupérer l'id source PMAC_LIVE
    id_source = get_source_mesure_id("PMAC_LIVE")
    logger.info(f"   → Source PMAC_LIVE : id={id_source}")
    
    # 2. Lire le référentiel
    df_raw = load_referentiel_excel()
    
    # 3. Transformer
    df_clean = transform_referentiel(df_raw)
    
    # 4. Charger en base
    nb_loaded = load_to_dwh(df_clean, id_source)
    
    # 5. Résumé
    print_summary()
    
    logger.info("=" * 70)
    logger.info(f"🎉 Chargement terminé : {nb_loaded} points de mesure")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()