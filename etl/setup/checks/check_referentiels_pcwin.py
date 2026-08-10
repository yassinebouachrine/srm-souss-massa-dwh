"""Vérification globale des référentiels PCWIN chargés."""
import pandas as pd
from etl.common.db import read_sql

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 220)


def section(title: str):
    print("\n" + "=" * 80)
    print(f"🔎 {title}")
    print("=" * 80)


# ═══ 1. VÉRIFICATION SOURCE PCWIN ═══
section("SOURCE PCWIN dans DIM_SOURCE_MESURE")
df = read_sql("SELECT * FROM dwh.dim_source_mesure WHERE code_source = 'PCWIN'")
print(df.to_string(index=False))

# ═══ 2. STATIONS PCWIN ═══
section("STATIONS PCWIN dans DIM_POINT_MESURE")
df = read_sql("""
    SELECT groupe_mesure, COUNT(*) AS nb_stations
    FROM dwh.dim_point_mesure
    WHERE id_source_mesure = (SELECT id_source_mesure FROM dwh.dim_source_mesure WHERE code_source = 'PCWIN')
    GROUP BY groupe_mesure
    ORDER BY nb_stations DESC;
""")
print(df.to_string(index=False))

# ═══ 3. LABELS CANAUX ═══
section("MAP CANAL LABEL")
df = read_sql("""
    SELECT voie, COUNT(*) AS nb
    FROM dwh.dim_canal_label
    GROUP BY voie
    ORDER BY nb DESC;
""")
print(df.to_string(index=False))

section("ÉCHANTILLON CANAL LABEL")
df = read_sql("""
    SELECT key_canal, canal_label
    FROM dwh.dim_canal_label
    ORDER BY id_pmac, canal
    LIMIT 15;
""")
print(df.to_string(index=False))

# ═══ 4. GROUPES ═══
section("GROUPES POINTS + BRIDGE")
df = read_sql("""
    SELECT g.nom_groupe, COUNT(b.id_point_mesure) AS nb_points
    FROM dwh.dim_groupe_points g
    LEFT JOIN dwh.bridge_groupe_point b ON g.id_groupe_points = b.id_groupe_points
    GROUP BY g.nom_groupe
    ORDER BY nb_points DESC;
""")
print(df.to_string(index=False))

# ═══ 5. CROSS-CHECK CANAL_LABEL ↔ POINT_MESURE ═══
section("COUVERTURE CANAL_LABEL (points PMAC avec labels)")
df = read_sql("""
    SELECT 
        COUNT(DISTINCT dp.id_pmac) AS nb_points_pmac,
        COUNT(DISTINCT dcl.id_pmac) AS nb_points_avec_labels,
        COUNT(DISTINCT dcl.id_pmac) FILTER (WHERE dp.id_pmac IS NOT NULL) AS nb_matches
    FROM dwh.dim_point_mesure dp
    FULL OUTER JOIN dwh.dim_canal_label dcl ON dp.id_pmac = dcl.id_pmac
    WHERE dp.id_source_mesure IN (
        SELECT id_source_mesure FROM dwh.dim_source_mesure 
        WHERE code_source IN ('PMAC_LIVE', 'PMAC_ARCHIVE')
    );
""")
print(df.to_string(index=False))

print("\n" + "=" * 80)
print("🎉 Vérifications référentiels PCWIN terminées")
print("=" * 80)