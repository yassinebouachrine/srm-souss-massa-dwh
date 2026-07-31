"""Vérification du Bronze PMAC."""
import pandas as pd
from etl.common.io_utils import get_latest_parquet, read_parquet

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 240)


def check_bronze_pmac():
    print("\n" + "=" * 80)
    print("🔎 VÉRIFICATION BRONZE PMAC")
    print("=" * 80)
    
    try:
        path = get_latest_parquet("bronze", "pmac", "mesures")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return
    
    df = read_parquet(path)
    
    print(f"📁 Fichier : {path.name}")
    print(f"📊 Shape   : {df.shape}")
    print(f"📋 Colonnes: {list(df.columns)}")
    
    print(f"\n🔍 Aperçu (5 premières lignes) :")
    print(df.head())
    
    print(f"\n📈 Répartition par VOIE :")
    print(df["voie"].value_counts())
    
    print(f"\n📈 Répartition par SOURCE_CODE :")
    print(df["source_code"].value_counts())
    
    print(f"\n📈 Répartition par CANAL (top 15) :")
    print(df["canal"].value_counts().head(15))
    
    print(f"\n📈 PMAC_ID distincts : {df['pmac_id'].nunique()}")
    print(f"   Exemples : {sorted(df['pmac_id'].unique())[:15]}")
    
    print(f"\n📅 Plage temporelle :")
    print(f"   Min : {df['date_heure'].min()}")
    print(f"   Max : {df['date_heure'].max()}")
    print(f"   Nb jours distincts : {df['date_heure'].dt.date.nunique()}")
    
    print(f"\n📊 Fichiers sources traités : {df['fichier_source'].nunique()}")
    print(f"   Exemples : {sorted(df['fichier_source'].unique())[:5]}")
    
    print(f"\n🎯 Statistiques valeurs par voie :")
    for voie in df["voie"].unique():
        sub = df[df["voie"] == voie]["valeur_brute"]
        print(f"\n   {voie} :")
        print(f"      count  : {len(sub):,}")
        print(f"      min    : {sub.min()}")
        print(f"      max    : {sub.max()}")
        print(f"      moy    : {sub.mean():.2f}")
        print(f"      median : {sub.median():.2f}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    check_bronze_pmac()