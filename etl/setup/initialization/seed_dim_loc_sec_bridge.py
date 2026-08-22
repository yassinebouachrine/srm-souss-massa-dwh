"""
Seed DIM_LOC_SEC + BRIDGE_LOC_SEC_ETAGE
Source : Matrice Affectation Loc_Sec Etage.xlsx (onglet 'matrice')

Peuple :
1. dwh.dim_loc_sec       → 1 ligne par loc_sec unique
2. dwh.bridge_loc_sec_etage → M:N loc_sec ↔ étage avec pourcentage

Gère automatiquement :
- Pourcentage NULL → 100% (répartition 1:1)
- Répartitions multiples (ex: 10_18 → 50% ILLIGH + 50% HAY MOHAMMADI)
- Normalisation loc_sec (majuscules, sans espaces)
- Idempotence via ON CONFLICT

Exécution : python -m etl.setup.seed_dim_loc_sec_bridge
"""
import pandas as pd
from sqlalchemy import text

from etl.common.config import get_path, load_mapping
from etl.common.db import get_engine, read_sql
from etl.common.logger import get_logger

from etl.common.config import get_raw_source_path  


logger = get_logger(__name__)

SOURCE_NAME = "rendements"


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _normalize_etage_name(nom: str, mapping: dict) -> str:
    """Retourne le code_etage DWH depuis un nom Excel."""
    if not nom or pd.isna(nom):
        return None
    key = str(nom).upper().strip()
    key = " ".join(key.split())  # espaces multiples → 1 espace
    return mapping.get(key)


def _parse_pourcentage(v) -> float:
    """
    Convertit un pourcentage Excel en float.
    - NULL/vide → 1.0 (100%)
    - "50%" → 0.5
    - 0.5 → 0.5
    - "10%" → 0.1
    """
    if v is None or pd.isna(v):
        return 1.0
    
    s = str(v).strip().replace("%", "").replace(",", ".")
    if not s:
        return 1.0
    
    try:
        val = float(s)
        # Si > 1, on suppose que c'est un pourcentage (50 → 0.5)
        if val > 1:
            val = val / 100.0
        return val
    except (ValueError, TypeError):
        return 1.0


# ═══════════════════════════════════════════════════════════════
# LECTURE
# ═══════════════════════════════════════════════════════════════

def load_matrice() -> pd.DataFrame:
    """Charge la matrice d'affectation."""
    cfg = load_mapping(SOURCE_NAME, "rendements_config")
    filename = cfg["files"]["matrice_locsec"]
    sheet    = cfg["sheets"]["matrice_locsec"]
    
    filepath = get_raw_source_path("referentiels") / filename
    
    if not filepath.exists():
        raise FileNotFoundError(
            f"❌ Fichier introuvable : {filepath}\n"
            f"   Placez-le dans data/raw/referentiels/etoile_c/"
        )
    
    logger.info(f"📖 Lecture : {filename} (onglet '{sheet}')")
    df = pd.read_excel(filepath, sheet_name=sheet, engine="openpyxl")
    df.columns = [c.strip() for c in df.columns]
    
    logger.info(f"   → {len(df)} lignes brutes, colonnes : {list(df.columns)}")
    return df, cfg


# ═══════════════════════════════════════════════════════════════
# TRANSFORMATION
# ═══════════════════════════════════════════════════════════════

def transform_matrice(df: pd.DataFrame, cfg: dict) -> tuple:
    """
    Transforme le DataFrame brut en :
    - df_loc_sec : 1 ligne par loc_sec unique (pour DIM_LOC_SEC)
    - df_bridge  : associations loc_sec ↔ étage (pour BRIDGE_LOC_SEC_ETAGE)
    """
    logger.info("🔄 Transformation...")
    
    mapping_etages = cfg["etages_normalisation"]
    
    # Nettoyage
    df = df.copy()
    df["loc_sec"]     = df["loc_sec"].astype(str).str.strip()
    df["loc"]         = df["Loc"].astype(str).str.strip()
    df["secteur_com"] = df["Secteur_Com"].astype(str).str.strip()
    df["nom_etage"]   = df["NOM_ETAGE"].astype(str).str.strip()
    df["pourcentage"] = df["Pourcentage"].apply(_parse_pourcentage)
    df["loc_sec_norm"] = df["loc_sec"].str.upper().str.replace(" ", "")
    
    # Résolution code_etage
    df["code_etage"] = df["nom_etage"].apply(
        lambda x: _normalize_etage_name(x, mapping_etages)
    )
    
    # Détection rejets (étage introuvable)
    df_rejets = df[df["code_etage"].isna()].copy()
    if not df_rejets.empty:
        logger.warning(f"   ⚠️  {len(df_rejets)} lignes rejetées (étage inconnu) :")
        for etage in df_rejets["nom_etage"].unique():
            cnt = (df_rejets["nom_etage"] == etage).sum()
            logger.warning(f"      • '{etage}' : {cnt} lignes")
    
    df = df[df["code_etage"].notna()].copy()
    logger.info(f"   ✅ {len(df)} lignes valides après matching étage")
    
    # ─── Créer DIM_LOC_SEC (unique par loc_sec) ───
    df_loc_sec = (
        df[["loc_sec", "loc", "secteur_com", "loc_sec_norm"]]
        .drop_duplicates(subset=["loc_sec"])
        .sort_values("loc_sec")
        .reset_index(drop=True)
    )
    # Attribuer un id_loc_sec (à partir de 1, 0 réservé pour sentinel)
    df_loc_sec["id_loc_sec"] = range(1, len(df_loc_sec) + 1)
    
    logger.info(f"   📊 {len(df_loc_sec)} loc_sec distincts")
    
    # ─── Créer BRIDGE (avec pct_effectif normalisé) ───
    map_locsec_id = dict(zip(df_loc_sec["loc_sec"], df_loc_sec["id_loc_sec"]))
    
    df["id_loc_sec"] = df["loc_sec"].map(map_locsec_id)
    
    # Calculer pct_effectif : somme par loc_sec doit = 1.0
    somme_par_locsec = df.groupby("loc_sec")["pourcentage"].transform("sum")
    df["pct_effectif"] = df["pourcentage"] / somme_par_locsec
    
    df_bridge = df[[
        "id_loc_sec", "code_etage", "pourcentage", "pct_effectif"
    ]].copy()
    
    # Log répartitions multiples
    reparti = df.groupby("loc_sec").size()
    reparti_multi = reparti[reparti > 1]
    if len(reparti_multi) > 0:
        logger.info(f"   🔀 {len(reparti_multi)} loc_sec avec répartition multiple :")
        for loc_sec_key in reparti_multi.head(10).index:
            details = df[df["loc_sec"] == loc_sec_key][["nom_etage", "pourcentage"]]
            for _, row in details.iterrows():
                logger.info(f"      • {loc_sec_key} → {row['nom_etage']} ({row['pourcentage']*100:.0f}%)")
    
    return df_loc_sec, df_bridge


# ═══════════════════════════════════════════════════════════════
# CHARGEMENT
# ═══════════════════════════════════════════════════════════════

UPSERT_LOCSEC_SQL = """
INSERT INTO dwh.dim_loc_sec (id_loc_sec, code_loc_sec, loc, secteur_com, loc_sec_norm)
VALUES (:id_loc_sec, :code_loc_sec, :loc, :secteur_com, :loc_sec_norm)
ON CONFLICT (id_loc_sec) DO UPDATE SET
    code_loc_sec = EXCLUDED.code_loc_sec,
    loc          = EXCLUDED.loc,
    secteur_com  = EXCLUDED.secteur_com,
    loc_sec_norm = EXCLUDED.loc_sec_norm;
"""

UPSERT_BRIDGE_SQL = """
INSERT INTO dwh.bridge_loc_sec_etage (id_loc_sec, id_etage, pourcentage, pct_effectif)
VALUES (:id_loc_sec, :id_etage, :pourcentage, :pct_effectif)
ON CONFLICT (id_loc_sec, id_etage) DO UPDATE SET
    pourcentage   = EXCLUDED.pourcentage,
    pct_effectif  = EXCLUDED.pct_effectif;
"""


def load_dim_loc_sec(df: pd.DataFrame) -> int:
    """Charge DIM_LOC_SEC."""
    logger.info(f"📥 Chargement DIM_LOC_SEC ({len(df)} lignes)...")
    
    records = [
        {
            "id_loc_sec":   int(row["id_loc_sec"]),
            "code_loc_sec": row["loc_sec"],
            "loc":          row["loc"],
            "secteur_com":  row["secteur_com"],
            "loc_sec_norm": row["loc_sec_norm"],
        }
        for _, row in df.iterrows()
    ]
    
    engine = get_engine()
    stmt = text(UPSERT_LOCSEC_SQL)
    with engine.begin() as conn:
        for i in range(0, len(records), 100):
            conn.execute(stmt, records[i:i+100])
    
    logger.info(f"✅ {len(records)} loc_sec UPSERT")
    return len(records)


def load_bridge(df: pd.DataFrame) -> int:
    """Charge BRIDGE_LOC_SEC_ETAGE."""
    logger.info(f"📥 Chargement BRIDGE_LOC_SEC_ETAGE ({len(df)} lignes)...")
    
    # Récupérer id_etage depuis code_etage
    df_etages = read_sql("SELECT id_etage, code_etage FROM dwh.dim_etage")
    map_etage = dict(zip(df_etages["code_etage"], df_etages["id_etage"]))
    
    df = df.copy()
    df["id_etage"] = df["code_etage"].map(map_etage)
    
    nb_orphelins = df["id_etage"].isna().sum()
    if nb_orphelins > 0:
        logger.warning(f"   ⚠️  {nb_orphelins} lignes bridge orphelines (code_etage introuvable en base)")
        logger.warning(f"      Étages : {df[df['id_etage'].isna()]['code_etage'].unique().tolist()}")
        df = df[df["id_etage"].notna()].copy()
    
    records = [
        {
            "id_loc_sec":    int(row["id_loc_sec"]),
            "id_etage":      int(row["id_etage"]),
            "pourcentage":   float(row["pourcentage"]),
            "pct_effectif":  float(row["pct_effectif"]),
        }
        for _, row in df.iterrows()
    ]
    
    engine = get_engine()
    stmt = text(UPSERT_BRIDGE_SQL)
    with engine.begin() as conn:
        for i in range(0, len(records), 100):
            conn.execute(stmt, records[i:i+100])
    
    logger.info(f"✅ {len(records)} associations UPSERT")
    return len(records)


# ═══════════════════════════════════════════════════════════════
# RÉSUMÉ
# ═══════════════════════════════════════════════════════════════

def print_summary():
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DIM_LOC_SEC + BRIDGE_LOC_SEC_ETAGE")
    print("=" * 70)
    
    df = read_sql("""
        SELECT 
            COUNT(*) AS nb_total,
            COUNT(DISTINCT loc) AS nb_localites,
            COUNT(DISTINCT secteur_com) AS nb_secteurs_com
        FROM dwh.dim_loc_sec
        WHERE id_loc_sec > 0;
    """)
    print("DIM_LOC_SEC :")
    print(df.to_string(index=False))
    
    print("\nBRIDGE_LOC_SEC_ETAGE par étage :")
    df = read_sql("""
        SELECT 
            e.code_etage,
            e.nom_etage,
            COUNT(*) AS nb_loc_sec,
            AVG(b.pourcentage)::DECIMAL(5,4) AS pct_moyen
        FROM dwh.bridge_loc_sec_etage b
        JOIN dwh.dim_etage e ON b.id_etage = e.id_etage
        GROUP BY e.code_etage, e.nom_etage
        ORDER BY nb_loc_sec DESC;
    """)
    print(df.to_string(index=False))
    
    print("\nRépartitions multiples (loc_sec avec >1 étage) :")
    df = read_sql("""
        SELECT 
            ls.code_loc_sec,
            e.nom_etage,
            b.pourcentage,
            b.pct_effectif
        FROM dwh.bridge_loc_sec_etage b
        JOIN dwh.dim_loc_sec ls ON b.id_loc_sec = ls.id_loc_sec
        JOIN dwh.dim_etage e ON b.id_etage = e.id_etage
        WHERE b.id_loc_sec IN (
            SELECT id_loc_sec 
            FROM dwh.bridge_loc_sec_etage 
            GROUP BY id_loc_sec 
            HAVING COUNT(*) > 1
        )
        ORDER BY ls.code_loc_sec, e.nom_etage;
    """)
    print(df.to_string(index=False))
    print("=" * 70)


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    logger.info("=" * 70)
    logger.info("🌱 SEED DIM_LOC_SEC + BRIDGE_LOC_SEC_ETAGE")
    logger.info("=" * 70)
    
    # 1. Lecture
    df_raw, cfg = load_matrice()
    
    # 2. Transformation
    df_loc_sec, df_bridge = transform_matrice(df_raw, cfg)
    
    # 3. Chargement
    nb_ls = load_dim_loc_sec(df_loc_sec)
    nb_br = load_bridge(df_bridge)
    
    # 4. Résumé
    print_summary()
    
    logger.info("=" * 70)
    logger.info(f"🎉 Terminé : {nb_ls} loc_sec + {nb_br} associations bridge")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()