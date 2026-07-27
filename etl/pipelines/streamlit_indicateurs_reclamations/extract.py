"""
ETL - Streamlit Indicateurs & Réclamations
Étape : EXTRACT (Bronze)

Rôle :
- Lire les tables app_staging.staging_indicateurs_dp et staging_reclamations_dp
- Filtrer sur statut = 'valide_regional' (uniquement lots finalisés)
- Ajouter les métadonnées de traçabilité
- Sauvegarder en Parquet dans data/bronze/streamlit_indicateurs_reclamations/

Aucune transformation métier : on garde les données telles quelles depuis PG.
"""
from datetime import datetime
import pandas as pd

from etl.common.config import CONFIG
from etl.common.logger import get_logger
from etl.common.db import read_sql
from etl.common.io_utils import save_parquet

logger = get_logger(__name__)

SOURCE_NAME = "streamlit_indicateurs_reclamations"
SOURCE_CFG = CONFIG["sources"][SOURCE_NAME]


# ═══════════════════════════════════════════════════════════════
# REQUÊTES SQL
# ═══════════════════════════════════════════════════════════════

SQL_INDICATEURS = """
SELECT
    s.id_staging,
    s.lot_id,
    s.id_province,
    s.nom_province,
    s.id_centre,
    s.nom_centre,
    s.annee,
    s.mois,
    s.nom_mois,
    s.code_indicateur,
    s.libelle_indicateur,
    s.unite,
    s.categorie,
    s.valeur_indicateur,
    s.statut,
    s.soumis_par,
    s.date_soumission,
    s.valide_par_dp,
    s.date_validation_dp,
    s.valide_par_regional,
    s.date_validation_reg,
    s.date_creation,
    s.date_modification
FROM app_staging.staging_indicateurs_dp s
WHERE s.statut = :statut
ORDER BY s.id_staging;
"""

SQL_RECLAMATIONS = """
SELECT
    s.id_staging,
    s.lot_id,
    s.id_province,
    s.nom_province,
    s.id_centre,
    s.nom_centre,
    s.annee,
    s.mois,
    s.code_type,
    s.libelle_reclamation,
    s.categorie_reclamation,
    s.nombre_reclamations,
    s.temps_moyen_coupure_h,
    s.delai_moyen_traitement_j,
    s.valeur_brute,
    s.statut,
    s.soumis_par,
    s.date_soumission,
    s.valide_par_dp,
    s.date_validation_dp,
    s.valide_par_regional,
    s.date_validation_reg,
    s.date_creation,
    s.date_modification
FROM app_staging.staging_reclamations_dp s
WHERE s.statut = :statut
ORDER BY s.id_staging;
"""


# ═══════════════════════════════════════════════════════════════
# EXTRACTION
# ═══════════════════════════════════════════════════════════════

def _extract_indicateurs(date_extraction: datetime) -> pd.DataFrame:
    """Lit les indicateurs validés au niveau régional."""
    statut = SOURCE_CFG["statut_a_charger"]
    logger.info(f"📥 Extraction indicateurs (statut='{statut}')...")

    df = read_sql(SQL_INDICATEURS, params={"statut": statut})

    if df.empty:
        logger.warning("   ⚠️  Aucun indicateur validé trouvé")
        return df

    # Métadonnées de traçabilité
    df["source_table"]   = f"{SOURCE_CFG['schema_source']}.{SOURCE_CFG['table_indicateurs']}"
    df["date_extraction"] = date_extraction

    logger.info(f"   ✅ {len(df)} lignes extraites")
    logger.info(f"      Lots distincts    : {df['lot_id'].nunique()}")
    logger.info(f"      Provinces         : {df['nom_province'].nunique()}")
    logger.info(f"      Périodes          : {df['annee'].astype(str) + '-' + df['mois'].astype(str).str.zfill(2)}".split(":", 1)[0]
                + f" → {df['annee'].min()}-{str(df['mois'].min()).zfill(2)} à {df['annee'].max()}-{str(df['mois'].max()).zfill(2)}")

    return df


def _extract_reclamations(date_extraction: datetime) -> pd.DataFrame:
    """Lit les réclamations validées au niveau régional."""
    statut = SOURCE_CFG["statut_a_charger"]
    logger.info(f"📥 Extraction réclamations (statut='{statut}')...")

    df = read_sql(SQL_RECLAMATIONS, params={"statut": statut})

    if df.empty:
        logger.warning("   ⚠️  Aucune réclamation validée trouvée")
        return df

    df["source_table"]    = f"{SOURCE_CFG['schema_source']}.{SOURCE_CFG['table_reclamations']}"
    df["date_extraction"] = date_extraction

    # Distinguer standard vs personnalisée
    df["est_personnalisee_source"] = df["code_type"].str.startswith("DIVERS_CUSTOM_")

    nb_std    = (~df["est_personnalisee_source"]).sum()
    nb_custom = df["est_personnalisee_source"].sum()
    logger.info(f"   ✅ {len(df)} lignes extraites")
    logger.info(f"      Standards       : {nb_std}")
    logger.info(f"      Personnalisées  : {nb_custom}")
    logger.info(f"      Lots distincts  : {df['lot_id'].nunique()}")

    return df


# ═══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def run_extract() -> dict:
    """Exécute l'extraction complète (Bronze)."""
    logger.info("=" * 70)
    logger.info("🥉 BRONZE - EXTRACTION STREAMLIT INDICATEURS & RÉCLAMATIONS")
    logger.info(f"   Source : {SOURCE_CFG['schema_source']}.*")
    logger.info(f"   Filtre : statut = '{SOURCE_CFG['statut_a_charger']}'")
    logger.info("=" * 70)

    date_extraction = datetime.now()
    result = {"status": "success"}

    # ─── INDICATEURS ───
    df_ind = _extract_indicateurs(date_extraction)
    if not df_ind.empty:
        path = save_parquet(df_ind, "bronze", SOURCE_NAME, "indicateurs")
        result["bronze_indicateurs"] = str(path)
        result["nb_indicateurs"] = len(df_ind)
    else:
        result["nb_indicateurs"] = 0

    logger.info("-" * 70)

    # ─── RÉCLAMATIONS ───
    df_rec = _extract_reclamations(date_extraction)
    if not df_rec.empty:
        path = save_parquet(df_rec, "bronze", SOURCE_NAME, "reclamations")
        result["bronze_reclamations"] = str(path)
        result["nb_reclamations"] = len(df_rec)
    else:
        result["nb_reclamations"] = 0

    logger.info("=" * 70)
    logger.info("✅ EXTRACTION TERMINÉE")
    logger.info("=" * 70)

    return result


if __name__ == "__main__":
    result = run_extract()
    print("\n📋 Résultat :")
    for k, v in result.items():
        print(f"   • {k}: {v}")