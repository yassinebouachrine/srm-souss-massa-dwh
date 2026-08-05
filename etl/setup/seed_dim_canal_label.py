"""
Seed DIM_CANAL_LABEL depuis Map_CanalLabel.xlsx

Ce référentiel donne un libellé métier à chaque canal (KeyCanal = id_pmac|canal).
Ex: "0416|DEBIT_02" → "Débit Sortie 10 000"

Idempotent : ON CONFLICT (key_canal) DO UPDATE
Exécution : python -m etl.setup.seed_dim_canal_label
"""
from pathlib import Path
import pandas as pd
from sqlalchemy import text

from etl.common.config import get_path
from etl.common.db import get_engine, read_sql
from etl.common.logger import get_logger

logger = get_logger(__name__)

REFERENTIEL_FILENAME = "Map_CanalLabel.xlsx"
SHEET_NAME = "Feuil1"


def load_referentiel_excel() -> pd.DataFrame:
    """Charge le fichier Map_CanalLabel.xlsx."""
    filepath = get_path("raw") / "referentiels" / "etoile_b" / REFERENTIEL_FILENAME

    if not filepath.exists():
        raise FileNotFoundError(
            f"❌ Fichier introuvable : {filepath}\n"
            f"   Placez-le dans data/raw/referentiels/etoile_b/"
        )

    logger.info(f"📖 Lecture : {filepath.name}")
    df = pd.read_excel(filepath, sheet_name=SHEET_NAME, engine="openpyxl")
    logger.info(f"   → {len(df)} lignes brutes, colonnes : {list(df.columns)}")
    return df


def transform_referentiel(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Transforme le DataFrame brut."""
    logger.info("🔄 Transformation...")

    df = df_raw.copy()

    # Nettoyer colonnes
    df.columns = [c.strip() for c in df.columns]

    # Vérification colonnes attendues
    if "KeyCanal" not in df.columns or "CanalLabel" not in df.columns:
        raise ValueError(
            f"❌ Colonnes attendues : 'KeyCanal', 'CanalLabel'. Trouvées : {list(df.columns)}"
        )

    # Nettoyage valeurs
    df["key_canal"]   = df["KeyCanal"].astype(str).str.strip()
    df["canal_label"] = df["CanalLabel"].astype(str).str.strip()

    # Filtrer lignes invalides
    nb_avant = len(df)
    df = df[df["key_canal"].notna() & (df["key_canal"] != "")]
    df = df[df["canal_label"].notna() & (df["canal_label"] != "")]
    df = df[df["key_canal"].str.contains("\\|", na=False)]  # doit contenir "|"

    # Extraire id_pmac et canal depuis key_canal
    df[["id_pmac", "canal"]] = df["key_canal"].str.split("|", n=1, expand=True)
    df["id_pmac"] = df["id_pmac"].str.strip()
    df["canal"]   = df["canal"].str.strip()

    # Extraire voie et channel depuis canal (ex: "DEBIT_02" → voie="DEBIT", channel="02")
    def _split_canal(canal):
        if not canal or "_" not in canal:
            return canal, None
        parts = canal.split("_", 1)
        return parts[0], parts[1] if len(parts) > 1 else None

    df[["voie", "channel"]] = df["canal"].apply(
        lambda c: pd.Series(_split_canal(c))
    )

    logger.info(f"   ✅ {len(df)} lignes valides ({nb_avant - len(df)} filtrées)")

    # Détection doublons
    duplicates = df[df["key_canal"].duplicated(keep=False)]
    if not duplicates.empty:
        logger.warning(f"   ⚠️  {len(duplicates)} doublons key_canal détectés :")
        for kc in duplicates["key_canal"].unique():
            labels = df[df["key_canal"] == kc]["canal_label"].tolist()
            logger.warning(f"      • {kc} : {labels}")
        df = df.drop_duplicates(subset=["key_canal"], keep="first")

    return df


UPSERT_SQL = """
INSERT INTO dwh.dim_canal_label (
    key_canal, id_pmac, canal, canal_label, voie, channel,
    fichier_source_ref, date_modification
) VALUES (
    :key_canal, :id_pmac, :canal, :canal_label, :voie, :channel,
    :fichier_source_ref, CURRENT_TIMESTAMP
)
ON CONFLICT (key_canal) DO UPDATE SET
    canal_label         = EXCLUDED.canal_label,
    voie                = EXCLUDED.voie,
    channel             = EXCLUDED.channel,
    fichier_source_ref  = EXCLUDED.fichier_source_ref,
    date_modification   = CURRENT_TIMESTAMP;
"""


def load_to_dwh(df: pd.DataFrame) -> int:
    """Charge en base via UPSERT."""
    logger.info(f"📥 Chargement dans dwh.dim_canal_label ({len(df)} lignes)...")

    records = [
        {
            "key_canal":          row["key_canal"],
            "id_pmac":            row["id_pmac"],
            "canal":              row["canal"],
            "canal_label":        row["canal_label"],
            "voie":               row["voie"],
            "channel":            row["channel"],
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

    logger.info(f"✅ {total} lignes UPSERT dans dwh.dim_canal_label")
    return total


def print_summary():
    """Résumé après chargement."""
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DIM_CANAL_LABEL")
    print("=" * 70)

    df = read_sql("""
        SELECT 
            COUNT(*) AS nb_total,
            COUNT(DISTINCT id_pmac) AS nb_points_distincts,
            COUNT(DISTINCT voie) AS nb_voies
        FROM dwh.dim_canal_label;
    """)
    print(df.to_string(index=False))

    print("\n📊 RÉPARTITION PAR VOIE :")
    df = read_sql("""
        SELECT voie, COUNT(*) AS nb
        FROM dwh.dim_canal_label
        GROUP BY voie
        ORDER BY nb DESC;
    """)
    print(df.to_string(index=False))

    print("\n📊 ÉCHANTILLON (10 premiers) :")
    df = read_sql("""
        SELECT key_canal, canal_label, voie, channel
        FROM dwh.dim_canal_label
        ORDER BY id_pmac, canal
        LIMIT 10;
    """)
    print(df.to_string(index=False))
    print("=" * 70)


def main():
    logger.info("=" * 70)
    logger.info("🌱 SEED DIM_CANAL_LABEL")
    logger.info("=" * 70)

    df_raw = load_referentiel_excel()
    df_clean = transform_referentiel(df_raw)
    nb = load_to_dwh(df_clean)
    print_summary()

    logger.info("=" * 70)
    logger.info(f"🎉 Chargement terminé : {nb} canaux labellisés")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()