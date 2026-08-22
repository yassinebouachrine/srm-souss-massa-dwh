"""
Seed DIM_POINT_MESURE pour les stations PCWIN
Source : Groupes Points Mesures PCWIN pour PBI.xlsx

Convention : id_pmac = "PCWIN_<Station_ID>"
Ex: Station_ID=57 → id_pmac="PCWIN_57"

Le nom_point = Nom_Station (ex: "399 Départ DN600 T104 Drargua")
Le groupe_mesure = colonne "Groupe_Mesure" du fichier
La station_pcwin = Nom_Station (dupliqué pour référence)

Idempotent : ON CONFLICT (id_pmac) DO UPDATE
Exécution : python -m etl.setup.seed_dim_point_mesure_pcwin
"""
from pathlib import Path
import pandas as pd
from sqlalchemy import text

from etl.common.config import get_path
from etl.common.db import get_engine, read_sql
from etl.common.logger import get_logger

from etl.common.config import get_raw_source_path 


logger = get_logger(__name__)

REFERENTIEL_FILENAME = "Groupes Points Mesures PCWIN pour PBI.xlsx"
SHEET_NAME = "Feuil1"


def load_referentiel_excel() -> pd.DataFrame:
    """Charge le fichier référentiel."""
    filepath = get_raw_source_path("referentiels") / REFERENTIEL_FILENAME

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
    """Transforme les données brutes pour DIM_POINT_MESURE."""
    logger.info("🔄 Transformation...")

    df = df_raw.copy()
    df.columns = [c.strip() for c in df.columns]

    # Vérification colonnes
    required = ["Station_ID", "Nom_Station", "Groupe_Mesure"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"❌ Colonnes manquantes : {missing}. Trouvées : {list(df.columns)}")

    # Nettoyage
    df = df[df["Station_ID"].notna()]
    df = df[df["Nom_Station"].notna()]

    df["station_id"]    = df["Station_ID"].astype(int)
    df["id_pmac"]       = "PCWIN_" + df["station_id"].astype(str)
    df["nom_point"]     = df["Nom_Station"].astype(str).str.strip()
    df["station_pcwin"] = df["Nom_Station"].astype(str).str.strip()
    df["groupe_mesure"] = df["Groupe_Mesure"].apply(
    lambda x: None if pd.isna(x) or str(x).strip().lower() in ("", "nan") 
    else str(x).strip()
)

    # Détection amont/aval par mots-clés
    df["est_amont"] = df["nom_point"].str.contains("amont|AMONT", case=False, na=False, regex=True)
    df["est_aval"]  = df["nom_point"].str.contains("aval|AVAL",   case=False, na=False, regex=True)

    # Détection réservoir/modulateur (heuristique)
    df["est_reservoir"]  = df["nom_point"].str.contains(
        "reserv|RES |RESERVOIR|DEPART|SORTIE", case=False, na=False, regex=True
    )
    df["est_modulateur"] = False  # à définir manuellement si besoin

    # Points sans code numérique = agrégats (ex: "Facturation", "Somme GC ZI Ait Melloul")
    df["est_agregat"] = ~df["nom_point"].str.match(r"^\d+\s", na=False)

    logger.info(f"   ✅ {len(df)} stations valides")

    # Détection doublons
    duplicates = df[df["id_pmac"].duplicated(keep=False)]
    if not duplicates.empty:
        logger.warning(f"   ⚠️  {len(duplicates)} doublons id_pmac :")
        for pmac_id in duplicates["id_pmac"].unique():
            noms = df[df["id_pmac"] == pmac_id]["nom_point"].tolist()
            logger.warning(f"      • {pmac_id} : {noms}")
        df = df.drop_duplicates(subset=["id_pmac"], keep="first")

    return df


UPSERT_SQL = """
INSERT INTO dwh.dim_point_mesure (
    id_pmac, id_source_mesure, nom_point, station_pcwin, groupe_mesure,
    est_pression, est_debit, est_reservoir, est_modulateur,
    est_amont, est_aval,
    fichier_source_ref, est_actif, date_modification
) VALUES (
    :id_pmac, :id_source_mesure, :nom_point, :station_pcwin, :groupe_mesure,
    :est_pression, :est_debit, :est_reservoir, :est_modulateur,
    :est_amont, :est_aval,
    :fichier_source_ref, TRUE, CURRENT_TIMESTAMP
)
ON CONFLICT (id_pmac) DO UPDATE SET
    nom_point           = EXCLUDED.nom_point,
    station_pcwin       = EXCLUDED.station_pcwin,
    groupe_mesure       = EXCLUDED.groupe_mesure,
    est_reservoir       = EXCLUDED.est_reservoir,
    est_amont           = EXCLUDED.est_amont,
    est_aval            = EXCLUDED.est_aval,
    fichier_source_ref  = EXCLUDED.fichier_source_ref,
    date_modification   = CURRENT_TIMESTAMP;
"""


def get_source_mesure_id(code_source: str = "PCWIN") -> int:
    """Récupère l'id_source_mesure de PCWIN."""
    df = read_sql(
        "SELECT id_source_mesure FROM dwh.dim_source_mesure WHERE code_source = :code",
        params={"code": code_source}
    )
    if df.empty:
        raise ValueError(
            f"❌ Source '{code_source}' introuvable dans dim_source_mesure. "
            f"Exécutez d'abord 14_seed_dwh_source_mesure.sql"
        )
    return int(df.iloc[0]["id_source_mesure"])


def load_to_dwh(df: pd.DataFrame, id_source_mesure: int) -> int:
    """Charge dans dwh.dim_point_mesure."""
    logger.info(f"📥 Chargement dans dwh.dim_point_mesure ({len(df)} lignes)...")

    records = [
        {
            "id_pmac":            row["id_pmac"],
            "id_source_mesure":   id_source_mesure,
            "nom_point":          row["nom_point"],
            "station_pcwin":      row["station_pcwin"],
            "groupe_mesure":      row["groupe_mesure"],
            "est_pression":       False,  # sera mis à jour par le pipeline PCWIN
            "est_debit":          False,  # sera mis à jour par le pipeline PCWIN
            "est_reservoir":      bool(row["est_reservoir"]),
            "est_modulateur":     bool(row["est_modulateur"]),
            "est_amont":          bool(row["est_amont"]),
            "est_aval":           bool(row["est_aval"]),
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

    logger.info(f"✅ {total} stations UPSERT dans dwh.dim_point_mesure")
    return total


def print_summary():
    """Résumé après chargement."""
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DIM_POINT_MESURE — Stations PCWIN")
    print("=" * 70)

    df = read_sql("""
        SELECT 
            COUNT(*) AS nb_total_pcwin,
            COUNT(*) FILTER (WHERE est_reservoir)  AS nb_reservoir,
            COUNT(*) FILTER (WHERE est_amont)      AS nb_amont,
            COUNT(*) FILTER (WHERE est_aval)       AS nb_aval
        FROM dwh.dim_point_mesure
        WHERE id_source_mesure = (
            SELECT id_source_mesure FROM dwh.dim_source_mesure WHERE code_source = 'PCWIN'
        );
    """)
    print(df.to_string(index=False))

    print("\n📊 RÉPARTITION PAR GROUPE_MESURE :")
    df = read_sql("""
        SELECT groupe_mesure, COUNT(*) AS nb
        FROM dwh.dim_point_mesure
        WHERE id_source_mesure = (
            SELECT id_source_mesure FROM dwh.dim_source_mesure WHERE code_source = 'PCWIN'
        )
        GROUP BY groupe_mesure
        ORDER BY nb DESC;
    """)
    print(df.to_string(index=False))

    print("\n📊 ÉCHANTILLON (10 premières stations PCWIN) :")
    df = read_sql("""
        SELECT id_pmac, nom_point, groupe_mesure, est_reservoir
        FROM dwh.dim_point_mesure
        WHERE id_source_mesure = (
            SELECT id_source_mesure FROM dwh.dim_source_mesure WHERE code_source = 'PCWIN'
        )
        ORDER BY id_pmac
        LIMIT 10;
    """)
    print(df.to_string(index=False))
    print("=" * 70)


def main():
    logger.info("=" * 70)
    logger.info("🌱 SEED DIM_POINT_MESURE - Stations PCWIN")
    logger.info("=" * 70)

    id_source = get_source_mesure_id("PCWIN")
    logger.info(f"   → Source PCWIN : id={id_source}")

    df_raw = load_referentiel_excel()
    df_clean = transform_referentiel(df_raw)
    nb = load_to_dwh(df_clean, id_source)
    print_summary()

    logger.info("=" * 70)
    logger.info(f"🎉 Terminé : {nb} stations PCWIN chargées")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()