"""Vérification du Silver PMAC."""
import pandas as pd
from etl.common.io_utils import get_latest_parquet, read_parquet

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 240)


def check_silver_pmac():
    print("\n" + "=" * 80)
    print("🔎 VÉRIFICATION SILVER PMAC")
    print("=" * 80)
    
    try:
        path = get_latest_parquet("silver", "pmac", "mesures")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return
    
    df = read_parquet(path)
    
    print(f"📁 Fichier : {path.name}")
    print(f"📊 Shape   : {df.shape}")
    print(f"📋 Colonnes: {list(df.columns)}")
    
    print(f"\n🔍 Aperçu (5 lignes) :")
    print(df.head())
    
    # ─── Clés étrangères ───
    print(f"\n🔑 Clés étrangères :")
    print(f"   • id_temps distincts       : {df['id_temps'].nunique():,}")
    print(f"   • id_point_mesure distincts: {df['id_point_mesure'].nunique():,}")
    print(f"   • id_source_mesure         : {df['id_source_mesure'].unique().tolist()}")
    print(f"   • id_etage / id_secteur    : {df['id_etage'].unique().tolist()} / {df['id_secteur'].unique().tolist()}")
    
    # ─── Qualité ───
    print(f"\n🎯 Répartition par qualité_donnees :")
    print(df["qualite_donnees"].value_counts().to_string())
    
    # ─── Voies ───
    print(f"\n📊 Répartition par voie :")
    print(df["voie"].value_counts().to_string())
    
    # ─── Ventilation ───
    print(f"\n💧 Ventilation des mesures (non-NULL) :")
    print(f"   • pression_bar       : {df['pression_bar'].notna().sum():>7,}")
    print(f"   • pression_amont_bar : {df['pression_amont_bar'].notna().sum():>7,}")
    print(f"   • pression_aval_bar  : {df['pression_aval_bar'].notna().sum():>7,}")
    print(f"   • debit_m3_h         : {df['debit_m3_h'].notna().sum():>7,}")
    print(f"   • volume_15min       : {df['volume_15min'].notna().sum():>7,}")
    print(f"   • index_compteur     : {df['index_compteur'].notna().sum():>7,}")
    
    # ─── Focus SUSPECT ───
    df_suspect = df[df["qualite_donnees"] == "SUSPECT"]
    if not df_suspect.empty:
        print(f"\n⚠️  Focus SUSPECT ({len(df_suspect):,} lignes) :")
        print(f"   Par voie :")
        print(df_suspect["voie"].value_counts().to_string())
        print(f"\n   Top 10 PMAC concernés :")
        print(df_suspect.groupby("pmac_id").size().sort_values(ascending=False).head(10).to_string())
    
    # ─── Plage temporelle ───
    print(f"\n📅 Plage temporelle :")
    print(f"   Min : {df['date_heure'].min()}")
    print(f"   Max : {df['date_heure'].max()}")
    print(f"   Nb jours : {df['date_heure'].dt.date.nunique()}")
    
    # ─── Vérification des rejets ───
    print("\n" + "=" * 80)
    print("🚨 REJETS")
    print("=" * 80)
    try:
        path_rej = get_latest_parquet("rejects", "pmac", "mesures_rejets")
        df_rej = read_parquet(path_rej)
        print(f"📁 Fichier : {path_rej.name}")
        print(f"📊 {len(df_rej):,} lignes rejetées")
        print(f"\n📋 Motifs de rejet :")
        print(df_rej["motif_rejet"].value_counts().to_string())
        
        # Top PMAC rejetés
        if "point_mesure_introuvable" in df_rej["motif_rejet"].values:
            print(f"\n🔍 PMAC_IDs introuvables dans dim_point_mesure :")
            pmac_ko = df_rej[df_rej["motif_rejet"] == "point_mesure_introuvable"]["pmac_id"].value_counts()
            print(pmac_ko.head(20).to_string())
    except FileNotFoundError:
        print("(Aucun rejet)")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    check_silver_pmac()