"""
ETL - PMAC (Capteurs Pression / Débit / Index)
Étape : EXTRACT (Bronze)

Rôle :
- Scanner les dossiers PMAC (Live + Archive selon config)
- Filtrer les fichiers valides (skip *_ALM, *_LOG, BACKUP, ~$)
- Détecter le type de fichier : STANDARD (virgule) ou INX (tabulation)
- Parser chaque fichier avec le bon parseur
- Extraire PMAC_ID + Channel depuis le nom
- Détecter la voie (PRESSION / DEBIT / INDEX) depuis header + nom
- Consolider tout dans 1 DataFrame Parquet Bronze

Aucune transformation métier ici : on stocke la donnée brute normalisée.
"""
from pathlib import Path
from datetime import datetime
import re
import unicodedata
import pandas as pd

from etl.common.config import CONFIG, load_mapping, PROJECT_ROOT
from etl.common.logger import get_logger
from etl.common.io_utils import save_parquet

logger = get_logger(__name__)

SOURCE_NAME = "pmac"
SOURCE_CFG = CONFIG["sources"][SOURCE_NAME]


# ═══════════════════════════════════════════════════════════════
# HELPERS ENCODAGE
# ═══════════════════════════════════════════════════════════════

def _read_file_lines(filepath: Path) -> list[str]:
    """
    Lit un fichier texte avec auto-detect d'encodage.
    Essaie utf-8 → cp1252 → latin-1 (dans l'ordre configuré).
    """
    encodings = SOURCE_CFG.get("encodings_fallback", ["utf-8", "cp1252", "latin-1"])
    
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.readlines()
        except UnicodeDecodeError:
            continue
    
    # Dernier recours : lecture binaire + decode 'replace'
    logger.warning(f"⚠️  Encodage non détecté pour {filepath.name}, lecture forcée en latin-1")
    with open(filepath, "rb") as f:
        return f.read().decode("latin-1", errors="replace").splitlines(keepends=True)


# ═══════════════════════════════════════════════════════════════
# HELPERS FILTRAGE FICHIERS
# ═══════════════════════════════════════════════════════════════

def _is_file_ignored(filepath: Path) -> tuple[bool, str]:
    """
    Retourne (True, motif) si le fichier doit être ignoré.
    """
    name_upper = filepath.name.upper()
    path_upper = str(filepath).upper()
    
    # Patterns dans le nom
    for pattern in SOURCE_CFG.get("ignore_patterns", []):
        if pattern.upper() in name_upper:
            return True, f"pattern_nom:{pattern}"
    
    # Dossiers exclus
    for folder in SOURCE_CFG.get("ignore_folders", []):
        if folder.upper() in path_upper:
            return True, f"dossier:{folder}"
    
    return False, ""


def _list_pmac_files() -> list[dict]:
    """
    Liste tous les fichiers PMAC à traiter depuis les dossiers configurés.
    
    Retourne : [{'filepath': Path, 'source_code': str, 'type': str}, ...]
    """
    files = []
    
    for folder_cfg in SOURCE_CFG.get("raw_folders", []):
        folder_path = Path(folder_cfg["path"])
        
        # Résoudre chemin relatif vers PROJECT_ROOT si nécessaire
        if not folder_path.is_absolute():
            folder_path = PROJECT_ROOT / folder_path
        
        if not folder_path.exists():
            logger.warning(f"⚠️  Dossier introuvable : {folder_path}")
            continue
        
        pattern = SOURCE_CFG.get("file_pattern", "*.csv")
        found = list(folder_path.rglob(pattern))
        
        logger.info(f"📁 {folder_path.name} : {len(found)} fichier(s) trouvé(s)")
        
        for fp in found:
            ignored, motif = _is_file_ignored(fp)
            if ignored:
                logger.debug(f"   ⊘ Ignoré ({motif}) : {fp.name}")
                continue
            
            files.append({
                "filepath":    fp,
                "source_code": folder_cfg["source_code"],
                "folder_type": folder_cfg["type"],
            })
    
    return files


# ═══════════════════════════════════════════════════════════════
# HELPERS EXTRACTION MÉTADONNÉES
# ═══════════════════════════════════════════════════════════════

def _parse_filename(filename: str) -> dict:
    """
    Extrait les métadonnées depuis le nom du fichier.
    
    Ex:
      "0007_01.csv"       → {pmac_id: "0007", channel: "01", is_inx: False}
      "0055_03_INX.csv"   → {pmac_id: "0055", channel: "03", is_inx: True}
      "0416_02_INX.csv"   → {pmac_id: "0416", channel: "02", is_inx: True}
    """
    stem = Path(filename).stem  # sans extension
    is_inx = SOURCE_CFG.get("inx_pattern", "_INX").upper() in stem.upper()
    
    # Retirer le suffixe _INX si présent
    stem_clean = re.sub(r'_INX$', '', stem, flags=re.IGNORECASE)
    
    parts = stem_clean.split("_")
    pmac_id = parts[0] if len(parts) >= 1 else None
    channel = parts[1] if len(parts) >= 2 else "01"
    
    # Padding PMAC_ID sur 4 chiffres
    if pmac_id and pmac_id.isdigit():
        pmac_id = pmac_id.zfill(4)
    
    # Padding channel sur 2 chiffres
    if channel and channel.isdigit():
        channel = channel.zfill(2)
    
    return {
        "pmac_id": pmac_id,
        "channel": channel,
        "is_inx":  is_inx,
    }


def _detect_voie(header_text: str, unite_text: str, is_inx: bool, mapping: dict) -> tuple[str, str, bool, bool]:
    """
    Détecte la voie, l'unité, et les flags amont/aval.
    
    Logique en cascade :
      1. Si fichier INX          → INDEX
      2. Sinon, matcher libellé  (keywords)
      3. Sinon, matcher unité    (fallback)
      4. Sinon                   → AUTRE
    
    Détecte aussi si le libellé indique amont/aval.
    
    Retourne (voie, unite, est_amont, est_aval).
    """
    # Priorité 1 : INX
    if is_inx:
        return "INDEX", "m3", False, False
    
    header_lower = (header_text or "").lower().strip()
    unite_lower = (unite_text or "").lower().strip()
    
    # ─── Détection amont/aval ───
    est_amont = False
    est_aval  = False
    
    aa_cfg = mapping.get("amont_aval_detection", {})
    for kw in aa_cfg.get("amont_keywords", []):
        if kw.lower() in header_lower:
            est_amont = True
            break
    for kw in aa_cfg.get("aval_keywords", []):
        if kw.lower() in header_lower:
            est_aval = True
            break
    
    # ─── Priorité 2 : détection par mot-clé du libellé ───
    for voie_key, cfg in mapping["voie_detection"].items():
        for keyword in cfg["keywords"]:
            if keyword.lower() in header_lower:
                voie = voie_key.upper()
                unite = unite_text if unite_text else cfg.get("unite_default")
                return voie, unite, est_amont, est_aval
    
    # ─── Priorité 3 : détection par unité (fallback) ───
    unite_map = mapping.get("unite_to_voie", {})
    for unite_pattern, voie in unite_map.items():
        if unite_pattern.lower() == unite_lower:
            return voie, unite_text, est_amont, est_aval
    
    # ─── Aucune correspondance : AUTRE ───
    return "AUTRE", unite_text, est_amont, est_aval

# ═══════════════════════════════════════════════════════════════
# HELPERS PARSING DATES / VALEURS
# ═══════════════════════════════════════════════════════════════

# Pattern date : dd/MM/yyyy avec ou sans heure
RE_DATE_ONLY  = re.compile(r'^(\d{2}/\d{2}/\d{4})$')
RE_DATE_TIME  = re.compile(r'^(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}(?::\d{2})?)$')


def _parse_datetime(text: str) -> pd.Timestamp | None:
    """
    Parse une date au format dd/MM/yyyy [HH:mm[:ss]].
    Cas spéciaux :
      - "24/12/2025"           → 24/12/2025 00:00:00 (minuit implicite)
      - "24/12/2025 08:00:00"  → 24/12/2025 08:00:00
      - "24/12/2025 08:00"     → 24/12/2025 08:00:00
    Retourne None si invalide.
    """
    if not text:
        return None
    
    text = text.strip().strip('"').strip("'")
    
    # Cas 1 : Date seule (implicite = minuit)
    m = RE_DATE_ONLY.match(text)
    if m:
        try:
            return pd.to_datetime(m.group(1) + " 00:00:00", format="%d/%m/%Y %H:%M:%S")
        except (ValueError, TypeError):
            return None
    
    # Cas 2 : Date + heure
    m = RE_DATE_TIME.match(text)
    if m:
        date_part = m.group(1)
        time_part = m.group(2)
        # Ajouter les secondes si absentes
        if len(time_part) == 5:  # HH:mm
            time_part += ":00"
        try:
            return pd.to_datetime(
                f"{date_part} {time_part}",
                format="%d/%m/%Y %H:%M:%S"
            )
        except (ValueError, TypeError):
            return None
    
    return None


def _parse_valeur(text: str) -> float | None:
    """
    Parse une valeur numérique (gère virgule décimale française).
    """
    if not text or not text.strip():
        return None
    
    s = text.strip().strip('"').replace(",", ".").replace(" ", "").replace("\xa0", "")
    
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


# ═══════════════════════════════════════════════════════════════
# PARSER 1 : CSV STANDARD (PRESSION / DEBIT)
# ═══════════════════════════════════════════════════════════════

def _parse_csv_standard(filepath: Path, mapping: dict) -> tuple[pd.DataFrame, dict]:
    """
    Parse un fichier CSV standard (PRESSION ou DEBIT).
    
    Format attendu :
      Ligne 1     : "Site Name","55/TAMZART","PMAC ID:","0055","Channel No:","03"
      Lignes 2-8  : vides
      Ligne ~9    : "Time","Pression","m"  ou  "Time","Debit 2","m3/hr"
      Lignes 10+  : dd/MM/yyyy HH:mm:ss,valeur
    
    Retourne (df_data, metadata).
    """
    lines = _read_file_lines(filepath)
    
    metadata = {
        "site_name":   None,
        "voie":        "INDEX",
        "unite":       "m3",
        "col_libelle": None,
        "est_amont":   False,
        "est_aval":    False,
    }
    
    records = []
    header_found = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # ─── Détecter ligne 1 : Site Name ───
        if not metadata["site_name"] and "Site Name" in line:
            parts = [p.strip().strip('"') for p in line.split(",")]
            # Format: "Site Name","55/TAMZART","PMAC ID:","0055","Channel No:","03"
            if len(parts) >= 2:
                metadata["site_name"] = parts[1]
            continue
        
        # ─── Détecter header colonnes : "Time","<voie>","<unite>" ───
        if not header_found and "time" in line.lower() and "," in line:
            parts = [p.strip().strip('"') for p in line.split(",")]
            if len(parts) >= 2:
                metadata["col_libelle"] = parts[1]
                if len(parts) >= 3:
                    metadata["unite"] = parts[2]
                
                # Nouvelle détection en cascade : libellé → unité → AUTRE
                voie, unite, est_amont, est_aval = _detect_voie(
                    header_text=parts[1],
                    unite_text=metadata["unite"],
                    is_inx=False,
                    mapping=mapping,
                )
                metadata["voie"] = voie
                if not metadata["unite"]:
                    metadata["unite"] = unite
                metadata["est_amont"] = est_amont
                metadata["est_aval"]  = est_aval
                
                header_found = True
            continue
        
        # ─── Ligne de données : dd/MM/yyyy [HH:mm:ss],valeur ───
        if header_found and "," in line:
            parts = line.split(",", 1)  # split max 2 (au cas où virgule dans valeur)
            if len(parts) != 2:
                continue
            
            dt = _parse_datetime(parts[0])
            val = _parse_valeur(parts[1])
            
            if dt is not None and val is not None:
                records.append({"date_heure": dt, "valeur_brute": val})
        
        # ─── Ligne date isolée (ex: "23/12/2025" en tête de section) ───
        # → Ignorée si header pas encore trouvé, sinon ambiguë donc ignorée aussi
    
    df = pd.DataFrame(records)
    return df, metadata


# ═══════════════════════════════════════════════════════════════
# PARSER 2 : CSV INX (INDEX)
# ═══════════════════════════════════════════════════════════════

def _parse_csv_inx(filepath: Path, mapping: dict) -> tuple[pd.DataFrame, dict]:
    """
    Parse un fichier CSV INX (INDEX).
    
    Format attendu :
      Ligne 1  : Date - Heure<TAB>V_INDEX<n>
      Lignes 2+: dd/MM/yyyy HH:mm:ss<TAB>valeur
    """
    lines = _read_file_lines(filepath)
    
    metadata = {
        "site_name":   None,        # Pas dans les fichiers INX
        "voie":        "INDEX",
        "unite":       "m3",
        "col_libelle": None,
    }
    
    records = []
    header_found = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Header : "Date - Heure\tV_INDEX3"
        if not header_found and "date" in line.lower():
            parts = line.split("\t")
            if len(parts) >= 2:
                metadata["col_libelle"] = parts[1].strip()
                header_found = True
            continue
        
        # Données : "23/12/2025 08:00:00\t0.000000"
        if header_found and "\t" in line:
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            
            dt  = _parse_datetime(parts[0])
            val = _parse_valeur(parts[1])
            
            if dt is not None and val is not None:
                records.append({"date_heure": dt, "valeur_brute": val})
    
    df = pd.DataFrame(records)
    return df, metadata


# ═══════════════════════════════════════════════════════════════
# EXTRACTION D'UN FICHIER (dispatcher)
# ═══════════════════════════════════════════════════════════════

def _extract_file(file_info: dict, mapping: dict, date_extraction: datetime) -> pd.DataFrame:
    """
    Extrait un fichier PMAC (dispatch vers standard ou INX).
    """
    filepath = file_info["filepath"]
    source_code = file_info["source_code"]
    
    logger.info(f"📄 {filepath.name}")
    
    # 1. Parser le nom du fichier
    meta_name = _parse_filename(filepath.name)
    is_inx = meta_name["is_inx"]
    
    # 2. Choisir le parser
    if is_inx:
        df, meta_content = _parse_csv_inx(filepath, mapping)
    else:
        df, meta_content = _parse_csv_standard(filepath, mapping)
    
    if df.empty:
        logger.warning(f"   ⚠️  Aucune donnée extraite")
        return pd.DataFrame()
    
    # 3. Construire le canal (respect convention PBI)
    voie = meta_content.get("voie") or "AUTRE"
    canal = f"{voie}_{meta_name['channel']}" if meta_name["channel"] else voie
    
    # 4. Ajouter TOUTES les métadonnées à chaque ligne (14 colonnes au total)
    df["pmac_id"]         = meta_name["pmac_id"]
    df["channel"]         = meta_name["channel"]
    df["canal"]           = canal
    df["voie"]            = voie
    df["unite"]           = meta_content.get("unite")
    df["site_name"]       = meta_content.get("site_name")
    df["col_libelle"]     = meta_content.get("col_libelle")
    df["est_amont"]       = meta_content.get("est_amont", False)
    df["est_aval"]        = meta_content.get("est_aval", False)
    df["is_inx"]          = is_inx
    df["fichier_source"]  = filepath.name              # ← IMPORTANT
    df["source_code"]     = source_code                # ← IMPORTANT
    df["folder_type"]     = file_info["folder_type"]   # ← IMPORTANT
    df["date_extraction"] = date_extraction            # ← IMPORTANT
    
    logger.info(
        f"   → {len(df)} mesures | voie={voie} | canal={canal} "
        f"| site={meta_content.get('site_name')}"
    )
    
    return df

# ═══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def run_extract() -> dict:
    """
    Exécute l'extraction PMAC complète (Bronze).
    """
    logger.info("=" * 70)
    logger.info("🥉 BRONZE - EXTRACTION PMAC")
    logger.info("=" * 70)
    
    date_extraction = datetime.now()
    
    # 1. Charger le mapping métier
    mapping = load_mapping(SOURCE_NAME, "pmac_config")
    
    # 2. Lister les fichiers à traiter
    files = _list_pmac_files()
    if not files:
        logger.warning("⚠️  Aucun fichier PMAC trouvé")
        return {"status": "no_files", "nb_files": 0}
    
    logger.info(f"📊 Total : {len(files)} fichier(s) à traiter")
    logger.info("-" * 70)
    
    # 3. Extraire chaque fichier
    all_dfs = []
    nb_ok, nb_ko = 0, 0
    
    for i, file_info in enumerate(files, 1):
        try:
            df = _extract_file(file_info, mapping, date_extraction)
            if not df.empty:
                all_dfs.append(df)
                nb_ok += 1
            else:
                nb_ko += 1
        except Exception as e:
            logger.error(f"   ❌ Erreur : {e}", exc_info=True)
            nb_ko += 1
    
    logger.info("-" * 70)
    logger.info(f"✅ Fichiers OK : {nb_ok}  |  ❌ Fichiers KO : {nb_ko}")
    
    # 4. Consolider
    if not all_dfs:
        logger.warning("⚠️  Aucune donnée à sauvegarder")
        return {"status": "empty", "nb_files": len(files)}
    
    df_final = pd.concat(all_dfs, ignore_index=True)
    
    # Réordonner les colonnes pour la lisibilité
    cols_order = [
        "pmac_id", "channel", "canal", "voie", "unite",
        "date_heure", "valeur_brute",
        "site_name", "col_libelle", "est_amont", "est_aval", "is_inx",
        "fichier_source", "source_code", "folder_type",
        "date_extraction",
    ]
    df_final = df_final[[c for c in cols_order if c in df_final.columns]]
    
    # Statistiques
    logger.info(f"📊 TOTAL EXTRAIT : {len(df_final):,} mesures")
    logger.info(f"   • PMAC distincts : {df_final['pmac_id'].nunique()}")
    logger.info(f"   • Canaux distincts : {df_final['canal'].nunique()}")
    logger.info(f"   • Répartition voies :")
    for voie, cnt in df_final["voie"].value_counts().items():
        logger.info(f"      - {voie:10s} : {cnt:,}")
    logger.info(f"   • Plage temporelle : {df_final['date_heure'].min()} → {df_final['date_heure'].max()}")
    
    # 5. Sauvegarder en Parquet Bronze
    bronze_folder = SOURCE_CFG.get("bronze_folder", "pmac")
    path = save_parquet(df_final, "bronze", bronze_folder, "mesures")
    
    logger.info("=" * 70)
    logger.info("✅ EXTRACTION PMAC TERMINÉE")
    logger.info("=" * 70)
    
    return {
        "status":               "success",
        "nb_files":             len(files),
        "nb_files_ok":          nb_ok,
        "nb_files_ko":          nb_ko,
        "nb_mesures":           len(df_final),
        "nb_pmac_distincts":    int(df_final["pmac_id"].nunique()),
        "nb_canaux_distincts":  int(df_final["canal"].nunique()),
        "bronze_parquet":       str(path),
    }


if __name__ == "__main__":
    result = run_extract()
    print("\n📋 Résultat :")
    for k, v in result.items():
        print(f"   • {k}: {v}")