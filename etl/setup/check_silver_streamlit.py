"""Vérification du Silver Streamlit."""
import pandas as pd
from etl.common.io_utils import get_latest_parquet, read_parquet

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 220)


def check(name: str, layer: str = "silver"):
    print("\n" + "=" * 80)
    print(f"🔎 VÉRIFICATION {layer.upper()} STREAMLIT — {name.upper()}")
    print("=" * 80)
    try:
        path = get_latest_parquet(layer, "streamlit_indicateurs_reclamations", name)
        df = read_parquet(path)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return
    
    print(f"📁 Fichier : {path.name}")
    print(f"📊 Shape   : {df.shape}")
    print(f"📋 Colonnes: {list(df.columns)}")
    print(f"\n🔍 Aperçu (toutes les lignes) :")
    print(df.to_string(index=False))
    
    if "code_dp" in df.columns:
        print(f"\n📈 Répartition par DP :")
        print(df["code_dp"].value_counts())
    
    if "id_temps" in df.columns:
        print(f"\n📅 Plage id_temps : {df['id_temps'].min()} → {df['id_temps'].max()}")
    
    if "est_personnalisee_source" in df.columns:
        print(f"\n🏷️  Standards vs Personnalisées :")
        print(df["est_personnalisee_source"].value_counts())


if __name__ == "__main__":
    check("indicateurs", "silver")
    check("reclamations", "silver")
    
    print("\n\n" + "=" * 80)
    print("🚨 REJETS")
    print("=" * 80)
    check("indicateurs_rejets", "rejects")
    check("reclamations_rejets", "rejects")