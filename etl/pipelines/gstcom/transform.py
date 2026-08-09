"""
ETL - GSTCOM
Étape : TRANSFORM (Silver)

- Parser dates + valeurs numériques
- Construire loc_sec (loc + "_" + sec)
- Résoudre id_loc_sec depuis DIM_LOC_SEC
- Calculer nb_jours_releve, conso_rapportee, age_compteur
- Séparer :
  * df_clients (une ligne par police, distinct)
  * df_consommations (une ligne par police × mois)
  * df_anomalies (une ligne par police × mois avec anomalie non-normale)
"""
from datetime import datetime
import pandas as pd
import numpy as np

from etl.common.config import load_mapping
from etl.common.logger import get_logger
from etl.common.io_utils import save_parquet, get_latest_parquet, read_parquet
from etl.common.db import read_sql

logger = get_logger(__name__)

SOURCE_NAME = "gstcom"


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _parse_float(v) -> float:
    if pd.isna(v):
        return np.nan
    if isinstance(v, str):
        s = v.strip().replace(" ", "").replace("\xa0", "").replace("\u202f", "")
        s = s.replace(",", ".")
        if not s or s.lower() in ("nan", "none", "-"):
            return np.nan
        try:
            return float(s)
        except (ValueError, TypeError):
            return np.nan
    try:
        return float(v)
    except (ValueError, TypeError):
        return np.nan


def _parse_int(v):
    f = _parse_float(v)
    return int(f) if not pd.isna(f) else None


def _parse_date(v):
    if pd.isna(v) or v == "" or v == "nan":
        return None
    try:
        return pd.to_datetime(v, errors="coerce")
    except:
        return None


def _clean_str(v):
    if pd.isna(v) or str(v).strip().lower() in ("", "nan", "none"):
        return None
    return str(v).strip()


def _build_loc_sec(row) -> str:
    """Construit la clé loc_sec (ex: '10_100')."""
    loc = _clean_str(row.get("loc"))
    sec = _clean_str(row.get("sec"))
    if not loc or not sec:
        return None
    # Retirer les zéros non significatifs pour matcher le référentiel
    try:
        loc_clean = str(int(loc))
        sec_clean = str(int(sec))
        return f"{loc_clean}_{sec_clean}"
    except (ValueError, TypeError):
        return f"{loc}_{sec}"


# ═══════════════════════════════════════════════════════════════
# TRANSFORM
# ═══════════════════════════════════════════════════════════════

def transform_bronze(df_bronze: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Transformation générique du Bronze : parsing + enrichissement."""
    logger.info(f"🔄 Transformation Bronze ({len(df_bronze)} lignes)...")
    
    df = df_bronze.copy()
    
    # ─── 1. Nettoyer colonnes texte ───
    for col in ["loc", "sec", "police", "categorie", "tournee", "ordre_tournee",
                "numero_compteur", "matricule_lecteur", "code_anomalie_01", 
                "code_anomalie_02", "nom_client", "adresse"]:
        if col in df.columns:
            df[col] = df[col].apply(_clean_str)
    
    # ─── 2. Parser numériques ───
    for col in ["conso_reelle", "conso_facturee", "redressement", 
                "index_debut", "index_fin", "latitude", "longitude"]:
        if col in df.columns:
            df[col] = df[col].apply(_parse_float)
    
    for col in ["type_part_adm", "credit"]:
        if col in df.columns:
            df[col] = df[col].apply(_parse_int)
    
    # ─── 3. Parser dates ───
    for col in ["date_releve_debut", "date_releve_fin", "date_installation_compteur"]:
        if col in df.columns:
            df[col] = df[col].apply(_parse_date)
    
    # ─── 4. Construire loc_sec ───
    df["loc_sec_key"] = df.apply(_build_loc_sec, axis=1)
    
    # ─── 5. Résoudre id_loc_sec ───
    df_locsec_map = read_sql("SELECT id_loc_sec, code_loc_sec FROM dwh.dim_loc_sec")
    map_locsec = dict(zip(df_locsec_map["code_loc_sec"], df_locsec_map["id_loc_sec"]))
    df["id_loc_sec"] = df["loc_sec_key"].map(map_locsec)
    
    nb_orphelins = df["id_loc_sec"].isna().sum()
    if nb_orphelins > 0:
        logger.warning(f"   ⚠️  {nb_orphelins} lignes sans loc_sec dans le référentiel")
        orphelins = df[df["id_loc_sec"].isna()]["loc_sec_key"].value_counts().head(10)
        for k, v in orphelins.items():
            logger.warning(f"      • loc_sec='{k}' : {v} lignes")
    
    # ─── 6. Calculs dérivés ───
    # nb_jours_releve
    df["nb_jours_releve"] = (df["date_releve_fin"] - df["date_releve_debut"]).dt.days
    df.loc[df["nb_jours_releve"] < 0, "nb_jours_releve"] = None
    
    # conso_rapportee (mensualisée à 30 jours)
    nb_jours_ref = cfg["regles"]["nb_jours_reference"]
    df["conso_rapportee"] = np.where(
        (df["nb_jours_releve"] > 0) & df["conso_reelle"].notna(),
        df["conso_reelle"] * nb_jours_ref / df["nb_jours_releve"],
        np.nan,
    )
    
    # age_compteur en années
    today = pd.Timestamp.now().normalize()
    df["age_compteur_annees"] = np.where(
        df["date_installation_compteur"].notna(),
        (today - df["date_installation_compteur"]).dt.days / 365.25,
        np.nan,
    )
    
    # est_gros_conso
    cat_gc = cfg["regles"]["categorie_gros_conso"]
    df["est_gros_conso"] = df["categorie"] == cat_gc
    
    # id_temps depuis date_releve_fin (mois de facturation)
    df["id_temps"] = df["date_releve_fin"].apply(
        lambda d: int(pd.Timestamp(d).strftime("%Y%m01")) if pd.notna(d) else None
    )
    
    # id_type_anomalie depuis code_anomalie_02
    map_anom = cfg["codes_anomalies"]
    df["id_type_anomalie"] = df["code_anomalie_02"].map(map_anom).fillna(0).astype(int)
    
    # Résoudre id_etage via bridge (majoritaire ou split)
    # On va faire ça dans la fonction dédiée build_facts()
    
    logger.info(f"   ✅ Transform Bronze OK")
    logger.info(f"      Lignes avec id_loc_sec  : {df['id_loc_sec'].notna().sum()}")
    logger.info(f"      Lignes avec id_temps    : {df['id_temps'].notna().sum()}")
    logger.info(f"      Anomalies non-normales  : {(df['id_type_anomalie'] != 1).sum()}")
    logger.info(f"      Gros consommateurs      : {df['est_gros_conso'].sum()}")
    
    return df


def build_dim_client(df: pd.DataFrame) -> pd.DataFrame:
    """Extrait la dimension client (une ligne par police, dernière valeur connue)."""
    logger.info("👤 Construction DIM_CLIENT...")
    
    cols_dim = [
        "police", "numero_compteur", "id_loc_sec", "loc", "sec",
        "type_part_adm", "tournee", "ordre_tournee", "categorie",
        "nom_client", "adresse", "latitude", "longitude",
        "date_installation_compteur", "age_compteur_annees",
        "matricule_lecteur", "est_gros_conso",
        "fichier_source",
    ]
    cols_present = [c for c in cols_dim if c in df.columns]
    
    df_valid = df[df["police"].notna()].copy()
    
    # Garder la dernière ligne par police (tri par date_releve_fin desc)
    df_dim = (
        df_valid[cols_present + ["date_releve_fin"]]
        .sort_values("date_releve_fin", ascending=True)
        .drop_duplicates(subset=["police"], keep="last")
        .drop(columns=["date_releve_fin"])
        .reset_index(drop=True)
    )
    
    logger.info(f"   ✅ {len(df_dim)} clients distincts")
    return df_dim


def build_fait_consommation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construit le fait consommation, avec pondération par étage via bridge.
    
    Un client (loc_sec) peut être rattaché à N étages avec des %.
    → On explose la ligne en N lignes de fait, avec pct_repartition_etage.
    """
    logger.info("💧 Construction FAIT_CONSOMMATION_CLIENT...")
    
    # 1. Charger bridge loc_sec → étage
    df_bridge = read_sql("""
        SELECT id_loc_sec, id_etage, pct_effectif
        FROM dwh.bridge_loc_sec_etage
    """)
    
    # 2. Filtrer les lignes valides
    df_valid = df[
        df["id_loc_sec"].notna() 
        & df["id_temps"].notna()
        & df["police"].notna()
    ].copy()
    
    logger.info(f"   → {len(df_valid)} lignes valides / {len(df)} bronze")
    
    # 3. Jointure avec bridge (explosion 1:N)
    df_fact = df_valid.merge(df_bridge, on="id_loc_sec", how="left")
    
    nb_sans_etage = df_fact["id_etage"].isna().sum()
    if nb_sans_etage > 0:
        logger.warning(f"   ⚠️  {nb_sans_etage} lignes sans étage (loc_sec sans mapping bridge)")
        df_fact.loc[df_fact["id_etage"].isna(), "id_etage"] = 0
        df_fact.loc[df_fact["pct_effectif"].isna(), "pct_effectif"] = 1.0
    
    # 4. Renommer/sélectionner colonnes finales
    df_fact = df_fact.rename(columns={"pct_effectif": "pct_repartition_etage"})
    
    df_fact["id_secteur"] = 0  # secteur INCONNU par défaut
    
    cols_fait = [
        "id_temps", "police", "id_loc_sec", "id_etage", "id_secteur",
        "conso_reelle", "conso_facturee", "conso_rapportee",
        "credit", "redressement",
        "index_debut", "index_fin",
        "date_releve_debut", "date_releve_fin", "nb_jours_releve",
        "pct_repartition_etage",
        "fichier_source",
    ]
    df_fait = df_fact[cols_fait].reset_index(drop=True)
    
    # Cast types SQL
    df_fait["id_temps"]    = df_fait["id_temps"].astype("int64")
    df_fait["id_etage"]    = df_fait["id_etage"].astype("int64")
    df_fait["id_secteur"]  = df_fait["id_secteur"].astype("int64")
    df_fait["id_loc_sec"]  = df_fait["id_loc_sec"].astype("Int64")
    
    logger.info(f"   ✅ {len(df_fait)} lignes fait consommation (avec explosion étages)")
    
    return df_fait


def build_fait_anomalie(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    Construit le fait anomalie (uniquement les codes non-normaux).
    """
    logger.info("🚨 Construction FAIT_ANOMALIE_COMPTEUR...")
    
    codes_ignorer = cfg["regles"]["codes_ignorer"]
    
    df_anom = df[
        df["police"].notna()
        & df["id_temps"].notna()
        & df["code_anomalie_02"].notna()
        & ~df["code_anomalie_02"].isin(codes_ignorer)
    ].copy()
    
    logger.info(f"   → {len(df_anom)} anomalies non-normales détectées")
    
    if df_anom.empty:
        return pd.DataFrame()
    
    # Explosion par étage (comme conso)
    df_bridge = read_sql("""
        SELECT id_loc_sec, id_etage, pct_effectif
        FROM dwh.bridge_loc_sec_etage
    """)
    df_anom = df_anom.merge(df_bridge, on="id_loc_sec", how="left")
    df_anom.loc[df_anom["id_etage"].isna(), "id_etage"] = 0
    df_anom.loc[df_anom["pct_effectif"].isna(), "pct_effectif"] = 1.0
    
    df_anom = df_anom.rename(columns={"pct_effectif": "pct_repartition_etage"})
    
    df_anom["id_secteur"]           = 0
    df_anom["nb_anomalies"]         = 1
    df_anom["nb_clients_affectes"]  = 1
    
    cols_anom = [
        "id_temps", "police", "id_etage", "id_secteur", "id_type_anomalie",
        "nb_anomalies", "nb_clients_affectes",
        "date_releve_fin", "pct_repartition_etage",
        "fichier_source",
    ]
    df_fait = df_anom[cols_anom].rename(columns={"date_releve_fin": "date_releve"}).reset_index(drop=True)
    
    df_fait["id_temps"]         = df_fait["id_temps"].astype("int64")
    df_fait["id_etage"]         = df_fait["id_etage"].astype("int64")
    df_fait["id_secteur"]       = df_fait["id_secteur"].astype("int64")
    df_fait["id_type_anomalie"] = df_fait["id_type_anomalie"].astype("int64")
    
    # Répartition anomalies
    stats = df_fait["id_type_anomalie"].value_counts()
    logger.info(f"   📊 Répartition anomalies :")
    df_types = read_sql("SELECT id_type_anomalie, libelle_anomalie FROM dwh.dim_type_anomalie")
    map_type = dict(zip(df_types["id_type_anomalie"], df_types["libelle_anomalie"]))
    for id_type, cnt in stats.items():
        libelle = map_type.get(id_type, "?")
        logger.info(f"      • {libelle:35s} : {cnt}")
    
    logger.info(f"   ✅ {len(df_fait)} lignes fait anomalie")
    return df_fait


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def run_transform() -> dict:
    logger.info("=" * 70)
    logger.info("🥈 SILVER - TRANSFORMATION GSTCOM")
    logger.info("=" * 70)
    
    cfg = load_mapping(SOURCE_NAME, "gstcom_config")
    result = {"status": "success"}
    
    try:
        # 1. Lire Bronze
        path_bronze = get_latest_parquet("bronze", SOURCE_NAME, "clientele")
        df_bronze = read_parquet(path_bronze)
        logger.info(f"📖 Bronze : {len(df_bronze)} lignes")
        
        # 2. Transform générique
        df = transform_bronze(df_bronze, cfg)
        
        # 3. Construire 3 datasets Silver
        df_dim_client   = build_dim_client(df)
        df_fait_conso   = build_fait_consommation(df)
        df_fait_anomalie = build_fait_anomalie(df, cfg)
        
        # 4. Sauvegardes
        logger.info("-" * 70)
        p = save_parquet(df_dim_client, "silver", SOURCE_NAME, "dim_client")
        result["silver_dim_client"] = str(p)
        result["nb_clients"] = len(df_dim_client)
        
        p = save_parquet(df_fait_conso, "silver", SOURCE_NAME, "fait_consommation")
        result["silver_fait_conso"] = str(p)
        result["nb_consommations"] = len(df_fait_conso)
        
        if not df_fait_anomalie.empty:
            p = save_parquet(df_fait_anomalie, "silver", SOURCE_NAME, "fait_anomalie")
            result["silver_fait_anomalie"] = str(p)
            result["nb_anomalies"] = len(df_fait_anomalie)
        
    except Exception as e:
        logger.error(f"❌ Erreur : {e}", exc_info=True)
        result["status"] = "error"
        result["error"] = str(e)
    
    logger.info("=" * 70)
    logger.info("✅ TRANSFORMATION TERMINÉE")
    logger.info("=" * 70)
    return result


if __name__ == "__main__":
    result = run_transform()
    import json
    print(json.dumps(result, indent=2, default=str))