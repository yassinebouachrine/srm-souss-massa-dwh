"""Vérification du Bronze Streamlit."""
import pandas as pd
from etl.common.io_utils import get_latest_parquet, read_parquet

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 220)


def check(name: str):
    print("\n" + "=" * 80)
    print(f"🔎 VÉRIFICATION BRONZE STREAMLIT — {name.upper()}")
    print("=" * 80)
    try:
        path = get_latest_parquet("bronze", "streamlit_indicateurs_reclamations", name)
        df = read_parquet(path)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return

    print(f"📁 Fichier : {path.name}")
    print(f"📊 Shape   : {df.shape}")
    print(f"📋 Colonnes: {list(df.columns)}")
    print(f"\n🔍 Aperçu (5 lignes) :")
    print(df.head())

    if "nom_province" in df.columns:
        print(f"\n📈 Répartition par province :")
        print(df["nom_province"].value_counts())

    if "statut" in df.columns:
        print(f"\n📈 Répartition par statut (devrait être uniquement 'valide_regional') :")
        print(df["statut"].value_counts())

    if "annee" in df.columns and "mois" in df.columns:
        df["periode"] = df["annee"].astype(str) + "-" + df["mois"].astype(str).str.zfill(2)
        print(f"\n📅 Périodes :")
        print(df["periode"].value_counts().sort_index())

    if "lot_id" in df.columns:
        print(f"\n📦 Nombre de lots distincts : {df['lot_id'].nunique()}")
        print("Exemples de lots :")
        print(df["lot_id"].unique()[:5])

    if name == "reclamations" and "est_personnalisee_source" in df.columns:
        print(f"\n🏷️  Standards vs Personnalisées :")
        print(df["est_personnalisee_source"].value_counts())
        print(f"\n📝 Libellés personnalisés distincts :")
        custom = df[df["est_personnalisee_source"]][["code_type", "libelle_reclamation"]].drop_duplicates()
        print(custom.to_string(index=False))


if __name__ == "__main__":
    check("indicateurs")
    check("reclamations")