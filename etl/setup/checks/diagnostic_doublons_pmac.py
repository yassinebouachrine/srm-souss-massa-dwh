# etl/setup/diagnostic_doublons_pmac.py
"""Diagnostic : identifier la source des doublons temporels."""
import pandas as pd
from etl.common.io_utils import get_latest_parquet, read_parquet

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 240)


def diagnostic_doublons():
    print("\n" + "=" * 80)
    print("🔍 DIAGNOSTIC - Doublons temporels dans Bronze PMAC")
    print("=" * 80)
    
    path = get_latest_parquet("bronze", "pmac", "mesures")
    df = read_parquet(path)
    
    # Identifier les doublons sur (pmac_id, date_heure, voie)
    duplicates_mask = df.duplicated(subset=["pmac_id", "date_heure", "voie"], keep=False)
    df_dup = df[duplicates_mask].sort_values(["pmac_id", "date_heure", "voie", "canal"])
    
    print(f"\n📊 Total doublons : {len(df_dup):,}")
    print(f"📊 Clés en doublon : {df_dup.duplicated(subset=['pmac_id', 'date_heure', 'voie']).sum() + df_dup.duplicated(subset=['pmac_id', 'date_heure', 'voie'], keep='last').sum()}")
    
    # Analyse : viennent-ils du même fichier ou de fichiers différents ?
    print(f"\n🔎 Top 20 groupes de doublons :")
    groupes = df_dup.groupby(["pmac_id", "date_heure", "voie"]).agg(
        nb=("valeur_brute", "count"),
        fichiers=("fichier_source", lambda x: list(x.unique())),
        canaux=("canal", lambda x: list(x.unique())),
        valeurs=("valeur_brute", lambda x: list(x.round(3))),
    ).sort_values("nb", ascending=False).head(20)
    print(groupes.to_string())
    
    # Statistiques par nb de fichiers impliqués
    print(f"\n🔎 Répartition doublons par nb de fichiers impliqués :")
    dup_by_files = df_dup.groupby(["pmac_id", "date_heure", "voie"]).agg(
        nb_fichiers=("fichier_source", "nunique"),
    )
    print(dup_by_files["nb_fichiers"].value_counts().sort_index())
    
    # Top PMAC concernés
    print(f"\n🔎 Top 10 PMAC les plus impactés :")
    pmac_dup = df_dup.groupby("pmac_id").size().sort_values(ascending=False).head(10)
    print(pmac_dup.to_string())
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    diagnostic_doublons()