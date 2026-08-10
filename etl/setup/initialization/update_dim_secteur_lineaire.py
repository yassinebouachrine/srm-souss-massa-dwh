"""
Update DIM_SECTEUR avec les linéaires du fichier Linéaire Par Secteur 2026.xlsx

Matching flexible sur nom_secteur ou nom_secteur_hydraulique.

Exécution : python -m etl.setup.update_dim_secteur_lineaire
"""
import unicodedata
import pandas as pd
from sqlalchemy import text

from etl.common.config import get_path, load_mapping
from etl.common.db import get_engine, read_sql
from etl.common.logger import get_logger

logger = get_logger(__name__)

SOURCE_NAME = "rendements"


def _normalize(s: str) -> str:
    """Normalise pour matching robuste."""
    if not s or pd.isna(s):
        return ""
    t = unicodedata.normalize("NFD", str(s))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.upper().strip()
    t = " ".join(t.split())
    return t


def main():
    logger.info("=" * 70)
    logger.info("🔄 UPDATE DIM_SECTEUR.lineaire_m")
    logger.info("=" * 70)
    
    cfg = load_mapping(SOURCE_NAME, "rendements_config")
    filename = cfg["files"]["lineaire_secteur"]
    sheet    = cfg["sheets"]["lineaire_secteur"]
    
    filepath = get_path("raw") / "referentiels" / "etoile_c" / filename
    if not filepath.exists():
        raise FileNotFoundError(f"❌ {filepath}")
    
    logger.info(f"📖 Lecture : {filename}")
    df = pd.read_excel(filepath, sheet_name=sheet, engine="openpyxl")
    df.columns = [c.strip() for c in df.columns]
    
    df["nom_norm"]    = df["NOM_SEC_HY"].apply(_normalize)
    df["lineaire_m"]  = pd.to_numeric(df["Linéaire (m)"], errors="coerce")
    df = df[df["nom_norm"] != ""].copy()
    df = df[df["lineaire_m"].notna()].copy()
    
    logger.info(f"   → {len(df)} lignes à traiter")
    
    # Récupérer secteurs existants (matching sur nom_secteur OU nom_secteur_hydraulique)
    df_dwh = read_sql("""
        SELECT id_secteur, code_secteur, nom_secteur, nom_secteur_hydraulique
        FROM dwh.dim_secteur
        WHERE id_secteur > 0
    """)
    df_dwh["nom_secteur_norm"]  = df_dwh["nom_secteur"].apply(_normalize)
    df_dwh["nom_hydra_norm"]    = df_dwh["nom_secteur_hydraulique"].apply(_normalize)
    
    # Matching
    nb_ok, nb_ko = 0, 0
    unmatched = []
    engine = get_engine()
    
    with engine.begin() as conn:
        for _, row in df.iterrows():
            nom_norm = row["nom_norm"]
            lin_m    = float(row["lineaire_m"])
            
            # Match sur nom_secteur ou nom_secteur_hydraulique
            match = df_dwh[
                (df_dwh["nom_secteur_norm"] == nom_norm) |
                (df_dwh["nom_hydra_norm"]   == nom_norm)
            ]
            
            if match.empty:
                unmatched.append(row["NOM_SEC_HY"])
                nb_ko += 1
                continue
            
            id_secteur = int(match.iloc[0]["id_secteur"])
            conn.execute(
                text("UPDATE dwh.dim_secteur SET lineaire_m = :lin WHERE id_secteur = :id"),
                {"lin": lin_m, "id": id_secteur},
            )
            nb_ok += 1
    
    logger.info(f"✅ {nb_ok} UPDATE | ❌ {nb_ko} non matchés")
    
    if unmatched:
        logger.warning(f"   Secteurs non matchés :")
        for nom in unmatched[:20]:
            logger.warning(f"      • '{nom}'")


if __name__ == "__main__":
    main()