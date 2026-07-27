"""Vérification du Silver après transformation."""
import pandas as pd
from etl.common.io_utils import get_latest_parquet, read_parquet

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)


def check(name: str, layer: str = "silver"):
    print("\n" + "=" * 80)
    print(f"🔎 VÉRIFICATION {layer.upper()} — {name.upper()}")
    print("=" * 80)
    try:
        path = get_latest_parquet(layer, "indicateurs_reclamations", name)
        df = read_parquet(path)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return
    
    print(f"📁 Fichier : {path.name}")
    print(f"📊 Shape   : {df.shape}")
    print(f"📋 Colonnes: {list(df.columns)}")
    print(f"\n🔍 Aperçu (5 lignes) :")
    print(df.head())
    
    if "code_dp" in df.columns:
        print(f"\n📈 Répartition par DP :")
        print(df["code_dp"].value_counts())
    
    if "est_recap_dp" in df.columns:
        print(f"\n📈 Recap DP vs Centres :")
        print(df["est_recap_dp"].value_counts())
    
    if "id_temps" in df.columns:
        print(f"\n📅 Plage id_temps : {df['id_temps'].min()} → {df['id_temps'].max()}")
        print(f"   Nombre de périodes distinctes : {df['id_temps'].nunique()}")
    
    if "valeur" in df.columns:
        print(f"\n📊 Stats 'valeur' :")
        print(df["valeur"].describe())
    
    if "code_indicateur" in df.columns:
        print(f"\n📊 Nb par indicateur (top 10) :")
        print(df["code_indicateur"].value_counts().head(10))
    
    if "code_reclamation" in df.columns:
        print(f"\n📊 Nb par type réclamation :")
        print(df["code_reclamation"].value_counts())
        print(f"\n📊 Ventilation nb / temps / delai :")
        print(f"   nb_reclamations non NULL       : {df['nb_reclamations'].notna().sum()}")
        print(f"   temps_moyen_coupure non NULL   : {df['temps_moyen_coupure'].notna().sum()}")
        print(f"   delai_moyen_traitement non NULL: {df['delai_moyen_traitement'].notna().sum()}")


if __name__ == "__main__":
    check("indicateurs", "silver")
    check("reclamations", "silver")
    
    print("\n\n" + "=" * 80)
    print("🚨 REJETS")
    print("=" * 80)
    try:
        check("indicateurs_rejets", "rejects")
    except Exception:
        print("(Aucun rejet indicateurs)")
    try:
        check("reclamations_rejets", "rejects")
    except Exception:
        print("(Aucun rejet réclamations)")