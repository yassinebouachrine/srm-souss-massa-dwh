"""
ETL - GSTCOM
Étape : LOAD (Gold)

- UPSERT dim_client (par police)
- UPSERT fait_consommation_client (par client × mois × étage)
- UPSERT fait_anomalie_compteur (par client × mois × étage × type)
"""
from datetime import datetime
import pandas as pd
from sqlalchemy import text

from etl.common.logger import get_logger
from etl.common.db import get_engine, read_sql
from etl.common.io_utils import get_latest_parquet, read_parquet

logger = get_logger(__name__)

SOURCE_NAME = "gstcom"
BATCH_SIZE = 500


def _to_pg_int(v):
    if pd.isna(v): return None
    return int(v)

def _to_pg_float(v):
    if pd.isna(v): return None
    return float(v)

def _to_pg_str(v):
    if pd.isna(v): return None
    return str(v)

def _to_pg_date(v):
    if pd.isna(v): return None
    if isinstance(v, str):
        try:
            return pd.to_datetime(v).date()
        except:
            return None
    return pd.Timestamp(v).date()


# ═══════════════════════════════════════════════════════════════
# UPSERT DIM_CLIENT
# ═══════════════════════════════════════════════════════════════

UPSERT_DIM_CLIENT_SQL = """
INSERT INTO dwh.dim_client (
    police, numero_compteur, id_loc_sec, loc, sec,
    type_part_adm, tournee, ordre_tournee, categorie,
    nom_client, adresse, latitude, longitude,
    date_installation_compteur, age_compteur_annees,
    matricule_lecteur, est_gros_conso,
    fichier_source_ref, date_modification
) VALUES (
    :police, :numero_compteur, :id_loc_sec, :loc, :sec,
    :type_part_adm, :tournee, :ordre_tournee, :categorie,
    :nom_client, :adresse, :latitude, :longitude,
    :date_installation_compteur, :age_compteur_annees,
    :matricule_lecteur, :est_gros_conso,
    :fichier_source_ref, CURRENT_TIMESTAMP
)
ON CONFLICT (police) DO UPDATE SET
    numero_compteur              = EXCLUDED.numero_compteur,
    id_loc_sec                   = EXCLUDED.id_loc_sec,
    loc                          = EXCLUDED.loc,
    sec                          = EXCLUDED.sec,
    type_part_adm                = EXCLUDED.type_part_adm,
    tournee                      = EXCLUDED.tournee,
    ordre_tournee                = EXCLUDED.ordre_tournee,
    categorie                    = EXCLUDED.categorie,
    nom_client                   = EXCLUDED.nom_client,
    adresse                      = EXCLUDED.adresse,
    latitude                     = EXCLUDED.latitude,
    longitude                    = EXCLUDED.longitude,
    date_installation_compteur   = EXCLUDED.date_installation_compteur,
    age_compteur_annees          = EXCLUDED.age_compteur_annees,
    matricule_lecteur            = EXCLUDED.matricule_lecteur,
    est_gros_conso               = EXCLUDED.est_gros_conso,
    fichier_source_ref           = EXCLUDED.fichier_source_ref,
    date_modification            = CURRENT_TIMESTAMP;
"""


def load_dim_client(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    
    logger.info(f"📥 UPSERT DIM_CLIENT ({len(df)} lignes)...")
    
    records = [
        {
            "police":                     _to_pg_str(row["police"]),
            "numero_compteur":            _to_pg_str(row.get("numero_compteur")),
            "id_loc_sec":                 _to_pg_int(row.get("id_loc_sec")),
            "loc":                        _to_pg_str(row.get("loc")),
            "sec":                        _to_pg_str(row.get("sec")),
            "type_part_adm":              _to_pg_int(row.get("type_part_adm")),
            "tournee":                    _to_pg_str(row.get("tournee")),
            "ordre_tournee":              _to_pg_str(row.get("ordre_tournee")),
            "categorie":                  _to_pg_str(row.get("categorie")),
            "nom_client":                 _to_pg_str(row.get("nom_client")),
            "adresse":                    _to_pg_str(row.get("adresse")),
            "latitude":                   _to_pg_float(row.get("latitude")),
            "longitude":                  _to_pg_float(row.get("longitude")),
            "date_installation_compteur": _to_pg_date(row.get("date_installation_compteur")),
            "age_compteur_annees":        _to_pg_float(row.get("age_compteur_annees")),
            "matricule_lecteur":          _to_pg_str(row.get("matricule_lecteur")),
            "est_gros_conso":             bool(row.get("est_gros_conso", False)),
            "fichier_source_ref":         _to_pg_str(row.get("fichier_source")),
        }
        for _, row in df.iterrows()
    ]
    
    engine = get_engine()
    stmt = text(UPSERT_DIM_CLIENT_SQL)
    total = 0
    with engine.begin() as conn:
        for i in range(0, len(records), BATCH_SIZE):
            conn.execute(stmt, records[i:i+BATCH_SIZE])
            total += min(BATCH_SIZE, len(records) - i)
    
    logger.info(f"✅ {total} clients UPSERT")
    return total


# ═══════════════════════════════════════════════════════════════
# UPSERT FAIT_CONSOMMATION
# ═══════════════════════════════════════════════════════════════

UPSERT_CONSO_SQL = """
INSERT INTO dwh.fait_consommation_client (
    id_temps, id_client, id_etage, id_secteur, id_loc_sec,
    conso_reelle, conso_facturee, conso_rapportee, credit, redressement,
    index_debut, index_fin,
    date_releve_debut, date_releve_fin, nb_jours_releve,
    pct_repartition_etage,
    fichier_source, date_chargement
) VALUES (
    :id_temps, :id_client, :id_etage, :id_secteur, :id_loc_sec,
    :conso_reelle, :conso_facturee, :conso_rapportee, :credit, :redressement,
    :index_debut, :index_fin,
    :date_releve_debut, :date_releve_fin, :nb_jours_releve,
    :pct_repartition_etage,
    :fichier_source, :date_chargement
)
ON CONFLICT (id_client, id_temps, id_etage) DO UPDATE SET
    conso_reelle           = EXCLUDED.conso_reelle,
    conso_facturee         = EXCLUDED.conso_facturee,
    conso_rapportee        = EXCLUDED.conso_rapportee,
    credit                 = EXCLUDED.credit,
    redressement           = EXCLUDED.redressement,
    index_debut            = EXCLUDED.index_debut,
    index_fin              = EXCLUDED.index_fin,
    date_releve_debut      = EXCLUDED.date_releve_debut,
    date_releve_fin        = EXCLUDED.date_releve_fin,
    nb_jours_releve        = EXCLUDED.nb_jours_releve,
    pct_repartition_etage  = EXCLUDED.pct_repartition_etage,
    fichier_source         = EXCLUDED.fichier_source,
    date_chargement        = EXCLUDED.date_chargement;
"""


def load_fait_consommation(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    
    logger.info(f"📥 UPSERT FAIT_CONSOMMATION_CLIENT ({len(df)} lignes)...")
    
    # Résoudre id_client depuis police
    df_clients = read_sql("SELECT id_client, police FROM dwh.dim_client")
    map_client = dict(zip(df_clients["police"], df_clients["id_client"]))
    
    df = df.copy()
    df["id_client"] = df["police"].map(map_client)
    
    nb_orphelins = df["id_client"].isna().sum()
    if nb_orphelins > 0:
        logger.warning(f"   ⚠️  {nb_orphelins} lignes sans id_client")
        df = df[df["id_client"].notna()].copy()
    
    now = datetime.now()
    records = [
        {
            "id_temps":               _to_pg_int(row["id_temps"]),
            "id_client":              _to_pg_int(row["id_client"]),
            "id_etage":               _to_pg_int(row["id_etage"]),
            "id_secteur":             _to_pg_int(row["id_secteur"]),
            "id_loc_sec":             _to_pg_int(row.get("id_loc_sec")),
            "conso_reelle":           _to_pg_float(row.get("conso_reelle")),
            "conso_facturee":         _to_pg_float(row.get("conso_facturee")),
            "conso_rapportee":        _to_pg_float(row.get("conso_rapportee")),
            "credit":                 _to_pg_int(row.get("credit")),
            "redressement":           _to_pg_float(row.get("redressement")),
            "index_debut":            _to_pg_float(row.get("index_debut")),
            "index_fin":              _to_pg_float(row.get("index_fin")),
            "date_releve_debut":      _to_pg_date(row.get("date_releve_debut")),
            "date_releve_fin":        _to_pg_date(row.get("date_releve_fin")),
            "nb_jours_releve":        _to_pg_int(row.get("nb_jours_releve")),
            "pct_repartition_etage":  _to_pg_float(row.get("pct_repartition_etage")),
            "fichier_source":         _to_pg_str(row.get("fichier_source")),
            "date_chargement":        now,
        }
        for _, row in df.iterrows()
    ]
    
    engine = get_engine()
    stmt = text(UPSERT_CONSO_SQL)
    total = 0
    with engine.begin() as conn:
        for i in range(0, len(records), BATCH_SIZE):
            conn.execute(stmt, records[i:i+BATCH_SIZE])
            total += min(BATCH_SIZE, len(records) - i)
            if total % 2000 == 0 or total == len(records):
                logger.info(f"   → {total:,} / {len(records):,} ({100*total/len(records):.1f}%)")
    
    logger.info(f"✅ {total} lignes UPSERT")
    return total


# ═══════════════════════════════════════════════════════════════
# UPSERT FAIT_ANOMALIE
# ═══════════════════════════════════════════════════════════════

UPSERT_ANOMALIE_SQL = """
INSERT INTO dwh.fait_anomalie_compteur (
    id_temps, id_client, id_etage, id_secteur, id_type_anomalie,
    nb_anomalies, nb_clients_affectes,
    date_releve, pct_repartition_etage,
    fichier_source, date_chargement
) VALUES (
    :id_temps, :id_client, :id_etage, :id_secteur, :id_type_anomalie,
    :nb_anomalies, :nb_clients_affectes,
    :date_releve, :pct_repartition_etage,
    :fichier_source, :date_chargement
)
ON CONFLICT (id_client, id_temps, id_etage, id_type_anomalie) DO UPDATE SET
    nb_anomalies          = EXCLUDED.nb_anomalies,
    nb_clients_affectes   = EXCLUDED.nb_clients_affectes,
    date_releve           = EXCLUDED.date_releve,
    pct_repartition_etage = EXCLUDED.pct_repartition_etage,
    fichier_source        = EXCLUDED.fichier_source,
    date_chargement       = EXCLUDED.date_chargement;
"""


def load_fait_anomalie(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    
    logger.info(f"📥 UPSERT FAIT_ANOMALIE_COMPTEUR ({len(df)} lignes)...")
    
    df_clients = read_sql("SELECT id_client, police FROM dwh.dim_client")
    map_client = dict(zip(df_clients["police"], df_clients["id_client"]))
    
    df = df.copy()
    df["id_client"] = df["police"].map(map_client)
    df = df[df["id_client"].notna()].copy()
    
    now = datetime.now()
    records = [
        {
            "id_temps":               _to_pg_int(row["id_temps"]),
            "id_client":              _to_pg_int(row["id_client"]),
            "id_etage":               _to_pg_int(row["id_etage"]),
            "id_secteur":             _to_pg_int(row["id_secteur"]),
            "id_type_anomalie":       _to_pg_int(row["id_type_anomalie"]),
            "nb_anomalies":           _to_pg_int(row["nb_anomalies"]),
            "nb_clients_affectes":    _to_pg_int(row["nb_clients_affectes"]),
            "date_releve":            _to_pg_date(row.get("date_releve")),
            "pct_repartition_etage":  _to_pg_float(row.get("pct_repartition_etage")),
            "fichier_source":         _to_pg_str(row.get("fichier_source")),
            "date_chargement":        now,
        }
        for _, row in df.iterrows()
    ]
    
    engine = get_engine()
    stmt = text(UPSERT_ANOMALIE_SQL)
    total = 0
    with engine.begin() as conn:
        for i in range(0, len(records), BATCH_SIZE):
            conn.execute(stmt, records[i:i+BATCH_SIZE])
            total += min(BATCH_SIZE, len(records) - i)
    
    logger.info(f"✅ {total} anomalies UPSERT")
    return total


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def run_load() -> dict:
    logger.info("=" * 70)
    logger.info("🥇 GOLD - CHARGEMENT DWH GSTCOM")
    logger.info("=" * 70)
    
    result = {"status": "success"}
    
    try:
        # 1. DIM_CLIENT en premier (les faits en dépendent)
        p = get_latest_parquet("silver", SOURCE_NAME, "dim_client")
        df_client = read_parquet(p)
        result["nb_clients"] = load_dim_client(df_client)
        
        logger.info("-" * 70)
        
        # 2. FAIT_CONSOMMATION
        p = get_latest_parquet("silver", SOURCE_NAME, "fait_consommation")
        df_conso = read_parquet(p)
        result["nb_consommations"] = load_fait_consommation(df_conso)
        
        logger.info("-" * 70)
        
        # 3. FAIT_ANOMALIE (optionnel)
        try:
            p = get_latest_parquet("silver", SOURCE_NAME, "fait_anomalie")
            df_anom = read_parquet(p)
            result["nb_anomalies"] = load_fait_anomalie(df_anom)
        except FileNotFoundError:
            logger.info("ℹ️  Pas de fichier anomalies Silver (aucune anomalie détectée)")
            result["nb_anomalies"] = 0
        
    except Exception as e:
        logger.error(f"❌ Erreur : {e}", exc_info=True)
        result["status"] = "error"
        result["error"] = str(e)
    
    logger.info("=" * 70)
    logger.info("✅ CHARGEMENT TERMINÉ")
    logger.info("=" * 70)
    return result


if __name__ == "__main__":
    result = run_load()
    import json
    print(json.dumps(result, indent=2, default=str))