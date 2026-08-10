"""Vérification du Gold PCWIN après chargement DWH."""
import pandas as pd
from etl.common.db import read_sql

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 240)


def section(title: str):
    print("\n" + "=" * 80)
    print(f"🔎 {title}")
    print("=" * 80)


# ═══ 1. VOLUMÉTRIE PCWIN ═══
section("VOLUMÉTRIE PCWIN dans fait_mesure_temps_reel")
df = read_sql("""
    SELECT ds.code_source, COUNT(*) AS nb_mesures
    FROM dwh.fait_mesure_temps_reel f
    JOIN dwh.dim_source_mesure ds ON f.id_source_mesure = ds.id_source_mesure
    GROUP BY ds.code_source
    ORDER BY nb_mesures DESC;
""")
print(df.to_string(index=False))


# ═══ 2. RÉPARTITION VOIE (PCWIN uniquement) ═══
section("VOIES — PCWIN")
df = read_sql("""
    SELECT voie, COUNT(*) AS nb, COUNT(DISTINCT id_point_mesure) AS nb_points
    FROM dwh.fait_mesure_temps_reel f
    WHERE id_source_mesure = (SELECT id_source_mesure FROM dwh.dim_source_mesure WHERE code_source = 'PCWIN')
    GROUP BY voie
    ORDER BY nb DESC;
""")
print(df.to_string(index=False))


# ═══ 3. QUALITÉ ═══
section("QUALITÉ — PCWIN")
df = read_sql("""
    SELECT qualite_donnees, COUNT(*) AS nb,
           ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
    FROM dwh.fait_mesure_temps_reel
    WHERE id_source_mesure = (SELECT id_source_mesure FROM dwh.dim_source_mesure WHERE code_source = 'PCWIN')
    GROUP BY qualite_donnees
    ORDER BY nb DESC;
""")
print(df.to_string(index=False))


# ═══ 4. TOP STATIONS ═══
section("TOP 15 STATIONS PCWIN")
df = read_sql("""
    SELECT dp.id_pmac, dp.nom_point, dp.groupe_mesure,
           COUNT(*) AS nb_mesures,
           COUNT(DISTINCT f.canal) AS nb_canaux
    FROM dwh.fait_mesure_temps_reel f
    JOIN dwh.dim_point_mesure dp ON f.id_point_mesure = dp.id_point_mesure
    WHERE f.id_source_mesure = (SELECT id_source_mesure FROM dwh.dim_source_mesure WHERE code_source = 'PCWIN')
    GROUP BY dp.id_pmac, dp.nom_point, dp.groupe_mesure
    ORDER BY nb_mesures DESC
    LIMIT 15;
""")
print(df.to_string(index=False))


# ═══ 5. PÉRIODES ═══
section("PÉRIODES COUVERTES — PCWIN")
df = read_sql("""
    SELECT MIN(heure) AS date_min, MAX(heure) AS date_max,
           COUNT(DISTINCT DATE(heure)) AS nb_jours
    FROM dwh.fait_mesure_temps_reel
    WHERE id_source_mesure = (SELECT id_source_mesure FROM dwh.dim_source_mesure WHERE code_source = 'PCWIN');
""")
print(df.to_string(index=False))


# ═══ 6. VENTILATION ═══
section("VENTILATION — PCWIN")
df = read_sql("""
    SELECT 
        COUNT(*) FILTER (WHERE pression_bar IS NOT NULL)       AS n_pression,
        COUNT(*) FILTER (WHERE pression_amont_bar IS NOT NULL) AS n_pression_amont,
        COUNT(*) FILTER (WHERE pression_aval_bar IS NOT NULL)  AS n_pression_aval,
        COUNT(*) FILTER (WHERE debit_m3_h IS NOT NULL)         AS n_debit,
        COUNT(*) FILTER (WHERE volume_15min IS NOT NULL)       AS n_volume,
        COUNT(*) FILTER (WHERE index_compteur IS NOT NULL)     AS n_index
    FROM dwh.fait_mesure_temps_reel
    WHERE id_source_mesure = (SELECT id_source_mesure FROM dwh.dim_source_mesure WHERE code_source = 'PCWIN');
""")
print(df.to_string(index=False))


# ═══ 7. ÉCHANTILLON ═══
section("ÉCHANTILLON MESURES PCWIN")
df = read_sql("""
    SELECT 
        f.heure, dp.id_pmac, dp.nom_point,
        f.voie, f.canal,
        f.pression_bar, f.debit_m3_h, f.index_compteur,
        f.qualite_donnees, f.unite
    FROM dwh.fait_mesure_temps_reel f
    JOIN dwh.dim_point_mesure dp ON f.id_point_mesure = dp.id_point_mesure
    WHERE f.id_source_mesure = (SELECT id_source_mesure FROM dwh.dim_source_mesure WHERE code_source = 'PCWIN')
    ORDER BY RANDOM()
    LIMIT 10;
""")
print(df.to_string(index=False))


# ═══ 8. IDEMPOTENCE ═══
section("TEST IDEMPOTENCE PCWIN")
df = read_sql("""
    SELECT id_point_mesure, heure, voie, canal, COUNT(*) AS nb
    FROM dwh.fait_mesure_temps_reel
    WHERE id_source_mesure = (SELECT id_source_mesure FROM dwh.dim_source_mesure WHERE code_source = 'PCWIN')
    GROUP BY id_point_mesure, heure, voie, canal
    HAVING COUNT(*) > 1
    LIMIT 10;
""")
if df.empty:
    print("✅ Aucun doublon")
else:
    print(f"❌ {len(df)} doublons !")
    print(df.head())

print("\n" + "=" * 80)
print("🎉 Vérifications Gold PCWIN terminées")
print("=" * 80)