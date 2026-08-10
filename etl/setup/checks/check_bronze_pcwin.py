"""Vérification du Bronze PCWIN."""
import pandas as pd
from etl.common.io_utils import get_latest_parquet, read_parquet

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 240)


def check_bronze_pcwin():
    print("\n" + "=" * 80)
    print("🔎 VÉRIFICATION BRONZE PCWIN")
    print("=" * 80)

    try:
        path = get_latest_parquet("bronze", "pcwin", "mesures")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return

    df = read_parquet(path)

    print(f"📁 Fichier : {path.name}")
    print(f"📊 Shape   : {df.shape}")
    print(f"📋 Colonnes: {list(df.columns)}")

    print(f"\n🔍 Aperçu (5 lignes) :")
    print(df.head())

    print(f"\n📈 Stations distinctes : {df['station_id'].nunique()}")
    print(f"📈 Variables distinctes : {df['variable_id'].nunique()}")
    print(f"📈 id_pmac distincts    : {df['id_pmac'].nunique()}")

    print(f"\n📅 Plage temporelle :")
    print(f"   Min : {df['datehe'].min()}")
    print(f"   Max : {df['datehe'].max()}")
    print(f"   Nb jours : {df['datehe'].dt.date.nunique()}")

    print(f"\n📈 Répartition libellés (top 20) :")
    print(df["libelle_mesure"].value_counts().head(20).to_string())

    print(f"\n📈 Unités présentes :")
    print(df["unite"].value_counts().to_string())

    print(f"\n📊 Stats valeurs :")
    print(df["valeur"].describe().to_string())

    print("\n" + "=" * 80)


if __name__ == "__main__":
    check_bronze_pcwin()