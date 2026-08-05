"""Vérification du Silver PCWIN."""
import pandas as pd
from etl.common.io_utils import get_latest_parquet, read_parquet

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 240)


def check_silver_pcwin():
    print("\n" + "=" * 80)
    print("🔎 VÉRIFICATION SILVER PCWIN")
    print("=" * 80)

    try:
        path = get_latest_parquet("silver", "pcwin", "mesures")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return

    df = read_parquet(path)

    print(f"📁 Fichier : {path.name}")
    print(f"📊 Shape   : {df.shape}")
    print(f"📋 Colonnes: {list(df.columns)}")

    print(f"\n🔍 Aperçu (5 lignes) :")
    print(df.head())

    print(f"\n🔑 Clés étrangères :")
    print(f"   • id_temps distincts       : {df['id_temps'].nunique():,}")
    print(f"   • id_point_mesure distincts: {df['id_point_mesure'].nunique():,}")
    print(f"   • id_source_mesure         : {df['id_source_mesure'].unique().tolist()}")

    print(f"\n🎯 Répartition par qualité :")
    print(df["qualite_donnees"].value_counts().to_string())

    print(f"\n📊 Répartition par voie :")
    print(df["voie"].value_counts().to_string())

    print(f"\n📊 Répartition par canal_affichage :")
    print(df["canal_affichage"].value_counts().to_string())

    print(f"\n📊 Répartition par nature_mesure :")
    print(df["nature_mesure"].value_counts().to_string())

    print(f"\n📊 Répartition par granularité :")
    print(df["granularite"].value_counts().to_string())

    print(f"\n💧 Ventilation des mesures (non-NULL) :")
    print(f"   • pression_bar       : {df['pression_bar'].notna().sum():>7,}")
    print(f"   • pression_amont_bar : {df['pression_amont_bar'].notna().sum():>7,}")
    print(f"   • pression_aval_bar  : {df['pression_aval_bar'].notna().sum():>7,}")
    print(f"   • debit_m3_h         : {df['debit_m3_h'].notna().sum():>7,}")
    print(f"   • volume_15min       : {df['volume_15min'].notna().sum():>7,}")
    print(f"   • index_compteur     : {df['index_compteur'].notna().sum():>7,}")

    print("\n" + "=" * 80)
    print("🚨 REJETS")
    print("=" * 80)
    try:
        path_rej = get_latest_parquet("rejects", "pcwin", "mesures_rejets")
        df_rej = read_parquet(path_rej)
        print(f"📁 Fichier : {path_rej.name}")
        print(f"📊 {len(df_rej):,} lignes rejetées")
        print(f"\n📋 Motifs :")
        print(df_rej["motif_rejet"].value_counts().to_string())
    except FileNotFoundError:
        print("(Aucun rejet)")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    check_silver_pcwin()