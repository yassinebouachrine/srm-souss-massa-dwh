"""
Diagnostic : identifier les libellés de colonnes non reconnus (voie=AUTRE).
"""
import pandas as pd
from etl.common.io_utils import get_latest_parquet, read_parquet

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 240)
pd.set_option("display.max_rows", 100)


def diagnostic():
    print("\n" + "=" * 80)
    print("🔍 DIAGNOSTIC - Libellés de colonnes non reconnus (voie=AUTRE)")
    print("=" * 80)
    
    path = get_latest_parquet("bronze", "pmac", "mesures")
    df = read_parquet(path)
    
    # Filtrer voie=AUTRE
    df_autre = df[df["voie"] == "AUTRE"].copy()
    
    if df_autre.empty:
        print("✅ Aucune ligne en 'AUTRE' - tout est bien classé !")
        return
    
    print(f"\n📊 Total lignes AUTRE : {len(df_autre):,}")
    print(f"📊 Fichiers concernés : {df_autre['fichier_source'].nunique()}")
    
    # 1. Répartition par col_libelle (LE plus important !)
    print(f"\n🔎 LIBELLÉS COL_LIBELLE non reconnus (à ajouter au mapping) :")
    libelles = df_autre.groupby("col_libelle").agg(
        nb_lignes=("valeur_brute", "count"),
        nb_fichiers=("fichier_source", "nunique"),
        exemples_fichiers=("fichier_source", lambda x: list(x.unique())[:3]),
        unite=("unite", "first"),
    ).sort_values("nb_lignes", ascending=False)
    
    print(libelles.to_string())
    
    # 2. Répartition par canal
    print(f"\n🔎 Répartition par CANAL :")
    print(df_autre["canal"].value_counts().to_string())
    
    # 3. Échantillon de fichiers AUTRE_01
    print(f"\n🔎 Exemples de fichiers avec CANAL=AUTRE_01 (top 20) :")
    files_autre = df_autre[df_autre["canal"] == "AUTRE_01"]["fichier_source"].unique()[:20]
    for f in files_autre:
        libelle = df_autre[df_autre["fichier_source"] == f]["col_libelle"].iloc[0]
        print(f"   • {f}  →  col_libelle='{libelle}'")
    
    # 4. Statistiques valeurs pour deviner le type
    print(f"\n🔎 Stats valeurs pour AUTRE (peut aider à deviner) :")
    stats = df_autre.groupby("col_libelle")["valeur_brute"].describe()
    print(stats)
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    diagnostic()