"""
Update DIM_ETAGE avec les linéaires du fichier Linéaire Par étage.xlsx

Idempotent : UPDATE sur code_etage matché.
Ne crée PAS de nouveaux étages (utiliser 15_seed_dwh_etage.sql pour ça).

Exécution : python -m etl.setup.update_dim_etage_lineaire
"""
import pandas as pd
from sqlalchemy import text

from etl.common.config import get_path, load_mapping
from etl.common.db import get_engine, read_sql
from etl.common.logger import get_logger

logger = get_logger(__name__)

SOURCE_NAME = "rendements"


def main():
    logger.info("=" * 70)
    logger.info("🔄 UPDATE DIM_ETAGE.lineaire_km")
    logger.info("=" * 70)
    
    cfg = load_mapping(SOURCE_NAME, "rendements_config")
    filename = cfg["files"]["lineaire_etage"]
    sheet    = cfg["sheets"]["lineaire_etage"]
    mapping_etages = cfg["etages_normalisation"]
    
    filepath = get_path("raw") / "referentiels" / "etoile_c" / filename
    if not filepath.exists():
        raise FileNotFoundError(f"❌ {filepath}")
    
    logger.info(f"📖 Lecture : {filename}")
    df = pd.read_excel(filepath, sheet_name=sheet, engine="openpyxl")
    df.columns = [c.strip() for c in df.columns]
    
    # Colonnes attendues : NOM_ETAGE, Lineaire (km)
    df["nom_etage_norm"] = df["NOM_ETAGE"].astype(str).str.upper().str.strip()
    df["nom_etage_norm"] = df["nom_etage_norm"].apply(lambda x: " ".join(x.split()))
    df["code_etage"]     = df["nom_etage_norm"].map(mapping_etages)
    df["lineaire_km"]    = pd.to_numeric(df["Lineaire (km)"], errors="coerce")
    
    df_ok = df[df["code_etage"].notna() & df["lineaire_km"].notna()].copy()
    df_ko = df[df["code_etage"].isna()].copy()
    
    logger.info(f"   ✅ {len(df_ok)} étages à mettre à jour")
    if not df_ko.empty:
        logger.warning(f"   ⚠️  {len(df_ko)} étages non reconnus :")
        for nom in df_ko["NOM_ETAGE"].unique():
            logger.warning(f"      • '{nom}'")
    
    # UPDATE
    engine = get_engine()
    with engine.begin() as conn:
        for _, row in df_ok.iterrows():
            conn.execute(
                text("""
                    UPDATE dwh.dim_etage
                    SET lineaire_km = :lin
                    WHERE code_etage = :code
                """),
                {"lin": float(row["lineaire_km"]), "code": row["code_etage"]},
            )
    
    logger.info(f"✅ {len(df_ok)} UPDATE effectués")
    
    # Vérification
    print("\n" + "=" * 70)
    print("📊 LINÉAIRES DIM_ETAGE APRÈS UPDATE")
    print("=" * 70)
    df_verif = read_sql("""
        SELECT id_etage, code_etage, nom_etage, lineaire_km
        FROM dwh.dim_etage
        WHERE type_etage != 'Agrégation' AND id_etage > 0
        ORDER BY id_etage;
    """)
    print(df_verif.to_string(index=False))
    print("=" * 70)


if __name__ == "__main__":
    main()