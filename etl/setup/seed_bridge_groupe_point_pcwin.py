"""
Seed DIM_GROUPE_POINTS + BRIDGE_GROUPE_POINT pour PCWIN.

Depuis le fichier "Groupes Points Mesures PCWIN pour PBI.xlsx", on :
1. Crée les groupes distincts dans dwh.dim_groupe_points
   (ex: "SECTEURS AGADIR", "REUSE", "GROS CONSO", ...)
2. Associe chaque station PCWIN à son groupe dans bridge_groupe_point
   (coefficient = 1.0 par défaut)

Idempotent : ON CONFLICT
Exécution : python -m etl.setup.seed_bridge_groupe_point_pcwin
"""
import pandas as pd
from sqlalchemy import text

from etl.common.config import get_path
from etl.common.db import get_engine, read_sql
from etl.common.logger import get_logger

logger = get_logger(__name__)

REFERENTIEL_FILENAME = "Groupes Points Mesures PCWIN pour PBI.xlsx"
SHEET_NAME = "Feuil1"


def load_referentiel() -> pd.DataFrame:
    filepath = get_path("raw") / "referentiels" / "etoile_b" / REFERENTIEL_FILENAME
    if not filepath.exists():
        raise FileNotFoundError(f"❌ Fichier introuvable : {filepath}")
    df = pd.read_excel(filepath, sheet_name=SHEET_NAME, engine="openpyxl")
    df.columns = [c.strip() for c in df.columns]
    df = df[df["Station_ID"].notna()]
    df["id_pmac"]       = "PCWIN_" + df["Station_ID"].astype(int).astype(str)
    df["groupe_mesure"] = df["Groupe_Mesure"].astype(str).str.strip()
    df = df[df["groupe_mesure"].notna() & (df["groupe_mesure"] != "")]
    return df[["id_pmac", "groupe_mesure"]]


def seed_groupes(df: pd.DataFrame) -> dict:
    """Insère les groupes distincts et retourne {nom_groupe: id_groupe_points}."""
    groupes = sorted(df["groupe_mesure"].unique())
    logger.info(f"📥 {len(groupes)} groupes distincts à créer :")
    for g in groupes:
        logger.info(f"   • {g}")

    engine = get_engine()
    with engine.begin() as conn:
        for i, nom in enumerate(groupes, 1):
            conn.execute(
                text("""
                    INSERT INTO dwh.dim_groupe_points (nom_groupe, description_groupe, ordre_affichage)
                    VALUES (:nom, :desc, :ordre)
                    ON CONFLICT (nom_groupe) DO NOTHING
                """),
                {"nom": nom, "desc": f"Groupe PCWIN : {nom}", "ordre": i}
            )

    # Récupérer les IDs
    df_map = read_sql("SELECT id_groupe_points, nom_groupe FROM dwh.dim_groupe_points")
    return dict(zip(df_map["nom_groupe"], df_map["id_groupe_points"]))


def seed_bridge(df: pd.DataFrame, map_groupes: dict) -> int:
    """Crée les associations dans bridge_groupe_point."""
    # Récupérer id_point_mesure pour chaque id_pmac
    df_pts = read_sql(
        "SELECT id_pmac, id_point_mesure FROM dwh.dim_point_mesure "
        "WHERE id_source_mesure = (SELECT id_source_mesure FROM dwh.dim_source_mesure WHERE code_source = 'PCWIN')"
    )
    map_pts = dict(zip(df_pts["id_pmac"], df_pts["id_point_mesure"]))

    records = []
    for _, row in df.iterrows():
        id_pt = map_pts.get(row["id_pmac"])
        id_gr = map_groupes.get(row["groupe_mesure"])
        if id_pt is None:
            logger.warning(f"   ⚠️  Point introuvable : {row['id_pmac']} (a-t-on lancé seed_dim_point_mesure_pcwin ?)")
            continue
        if id_gr is None:
            logger.warning(f"   ⚠️  Groupe introuvable : {row['groupe_mesure']}")
            continue
        records.append({
            "id_groupe_points": id_gr,
            "id_point_mesure":  id_pt,
            "coefficient":      1.0,
            "ordre":            0,
        })

    logger.info(f"📥 {len(records)} associations bridge à insérer...")

    engine = get_engine()
    with engine.begin() as conn:
        for rec in records:
            conn.execute(
                text("""
                    INSERT INTO dwh.bridge_groupe_point (id_groupe_points, id_point_mesure, coefficient, ordre)
                    VALUES (:id_groupe_points, :id_point_mesure, :coefficient, :ordre)
                    ON CONFLICT (id_groupe_points, id_point_mesure) DO UPDATE SET
                        coefficient = EXCLUDED.coefficient,
                        ordre       = EXCLUDED.ordre
                """),
                rec,
            )

    logger.info(f"✅ {len(records)} associations UPSERT")
    return len(records)


def print_summary():
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ BRIDGE GROUPE-POINT (PCWIN)")
    print("=" * 70)

    df = read_sql("""
        SELECT g.nom_groupe, COUNT(b.id_point_mesure) AS nb_points
        FROM dwh.dim_groupe_points g
        LEFT JOIN dwh.bridge_groupe_point b ON g.id_groupe_points = b.id_groupe_points
        GROUP BY g.nom_groupe
        ORDER BY nb_points DESC;
    """)
    print(df.to_string(index=False))
    print("=" * 70)


def main():
    logger.info("=" * 70)
    logger.info("🌱 SEED BRIDGE GROUPE-POINT (PCWIN)")
    logger.info("=" * 70)

    df = load_referentiel()
    map_groupes = seed_groupes(df)
    nb = seed_bridge(df, map_groupes)
    print_summary()

    logger.info("=" * 70)
    logger.info(f"🎉 Terminé : {nb} associations créées")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()