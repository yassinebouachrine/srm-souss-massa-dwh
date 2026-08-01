"""Vérification du Gold PMAC après chargement DWH."""
import pandas as pd
from etl.common.db import read_sql

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 240)


def section(title: str):
    print("\n" + "=" * 80)
    print(f"🔎 {title}")
    print("=" * 80)


# ═══ 1. VOLUMÉTRIE ═══
section("VOLUMÉTRIE DWH — Étoile B (PMAC)")
df = read_sql("""
    SELECT 'fait_mesure_temps_reel' AS table_name, COUNT(*) AS nb_lignes
    FROM dwh.fait_mesure_temps_reel
    UNION ALL
    SELECT 'dim_point_mesure', COUNT(*) FROM dwh.dim_point_mesure
    UNION ALL
    SELECT 'dim_source_mesure', COUNT(*) FROM dwh.dim_source_mesure
    UNION ALL
    SELECT 'dim_etage', COUNT(*) FROM dwh.dim_etage
    UNION ALL
    SELECT 'dim_secteur', COUNT(*) FROM dwh.dim_secteur
    ORDER BY table_name;
""")
print(df.to_string(index=False))


# ═══ 2. RÉPARTITION PAR VOIE ═══
section("MESURES PAR VOIE")
df = read_sql("""
    SELECT voie, COUNT(*) AS nb_mesures,
           COUNT(DISTINCT id_point_mesure) AS nb_points,
           COUNT(DISTINCT canal) AS nb_canaux
    FROM dwh.fait_mesure_temps_reel
    GROUP BY voie
    ORDER BY nb_mesures DESC;
""")
print(df.to_string(index=False))


# ═══ 3. RÉPARTITION PAR SOURCE ═══
section("MESURES PAR SOURCE")
df = read_sql("""
    SELECT ds.code_source, ds.libelle_source, COUNT(*) AS nb_mesures
    FROM dwh.fait_mesure_temps_reel f
    JOIN dwh.dim_source_mesure ds ON f.id_source_mesure = ds.id_source_mesure
    GROUP BY ds.code_source, ds.libelle_source
    ORDER BY nb_mesures DESC;
""")
print(df.to_string(index=False))


# ═══ 4. RÉPARTITION PAR QUALITÉ ═══
section("RÉPARTITION QUALITÉ")
df = read_sql("""
    SELECT qualite_donnees, COUNT(*) AS nb,
           ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
    FROM dwh.fait_mesure_temps_reel
    GROUP BY qualite_donnees
    ORDER BY nb DESC;
""")
print(df.to_string(index=False))


# ═══ 5. TOP 15 POINTS DE MESURE (par nb de mesures) ═══
section("TOP 15 POINTS DE MESURE")
df = read_sql("""
    SELECT dp.id_pmac, dp.nom_point, dp.groupe_mesure,
           COUNT(*) AS nb_mesures,
           COUNT(DISTINCT f.voie) AS nb_voies,
           COUNT(DISTINCT f.canal) AS nb_canaux
    FROM dwh.fait_mesure_temps_reel f
    JOIN dwh.dim_point_mesure dp ON f.id_point_mesure = dp.id_point_mesure
    GROUP BY dp.id_pmac, dp.nom_point, dp.groupe_mesure
    ORDER BY nb_mesures DESC
    LIMIT 15;
""")
print(df.to_string(index=False))


# ═══ 6. PÉRIODES COUVERTES ═══
section("PÉRIODES COUVERTES")
df = read_sql("""
    SELECT 
        MIN(heure) AS date_min,
        MAX(heure) AS date_max,
        COUNT(DISTINCT DATE(heure)) AS nb_jours_distincts,
        COUNT(DISTINCT id_temps) AS nb_id_temps
    FROM dwh.fait_mesure_temps_reel;
""")
print(df.to_string(index=False))


# ═══ 7. VENTILATION DES MESURES (colonnes non-NULL) ═══
section("VENTILATION MESURES (colonnes non-NULL)")
df = read_sql("""
    SELECT 
        COUNT(*) FILTER (WHERE pression_bar IS NOT NULL)         AS n_pression,
        COUNT(*) FILTER (WHERE pression_amont_bar IS NOT NULL)   AS n_pression_amont,
        COUNT(*) FILTER (WHERE pression_aval_bar IS NOT NULL)    AS n_pression_aval,
        COUNT(*) FILTER (WHERE debit_m3_h IS NOT NULL)           AS n_debit,
        COUNT(*) FILTER (WHERE volume_15min IS NOT NULL)         AS n_volume,
        COUNT(*) FILTER (WHERE index_compteur IS NOT NULL)       AS n_index
    FROM dwh.fait_mesure_temps_reel;
""")
print(df.to_string(index=False))


# ═══ 8. ÉCHANTILLON DE MESURES (10 lignes variées) ═══
section("ÉCHANTILLON 10 MESURES (jointure complète)")
df = read_sql("""
    SELECT 
        f.heure,
        dp.id_pmac,
        dp.nom_point,
        f.voie,
        f.canal,
        f.pression_bar,
        f.pression_amont_bar,
        f.pression_aval_bar,
        f.debit_m3_h,
        f.index_compteur,
        f.qualite_donnees,
        f.unite
    FROM dwh.fait_mesure_temps_reel f
    JOIN dwh.dim_point_mesure dp ON f.id_point_mesure = dp.id_point_mesure
    ORDER BY RANDOM()
    LIMIT 10;
""")
print(df.to_string(index=False))


# ═══ 9. FOCUS SUSPECT ═══
section("FOCUS SUSPECT — Top 10 PMAC")
df = read_sql("""
    SELECT dp.id_pmac, dp.nom_point, dp.groupe_mesure,
           COUNT(*) AS nb_suspect,
           MIN(f.pression_bar) AS min_pression,
           MAX(f.pression_bar) AS max_pression
    FROM dwh.fait_mesure_temps_reel f
    JOIN dwh.dim_point_mesure dp ON f.id_point_mesure = dp.id_point_mesure
    WHERE f.qualite_donnees = 'SUSPECT'
    GROUP BY dp.id_pmac, dp.nom_point, dp.groupe_mesure
    ORDER BY nb_suspect DESC
    LIMIT 10;
""")
print(df.to_string(index=False))


# ═══ 10. TEST IDEMPOTENCE ═══
section("TEST IDEMPOTENCE — Doublons ? (doit être vide)")
df = read_sql("""
    SELECT id_point_mesure, heure, voie, canal, COUNT(*) AS nb
    FROM dwh.fait_mesure_temps_reel
    GROUP BY id_point_mesure, heure, voie, canal
    HAVING COUNT(*) > 1
    LIMIT 10;
""")
if df.empty:
    print("✅ Aucun doublon — contrainte unique respectée")
else:
    print(f"❌ {len(df)} doublons détectés !")
    print(df.head())


# ═══ 11. COHÉRENCE MULTI-CANAUX PAR PMAC ═══
section("COHÉRENCE MULTI-CANAUX (points PMAC avec plusieurs canaux)")
df = read_sql("""
    SELECT dp.id_pmac, dp.nom_point,
           COUNT(DISTINCT f.canal) AS nb_canaux,
           STRING_AGG(DISTINCT f.canal, ', ' ORDER BY f.canal) AS canaux
    FROM dwh.fait_mesure_temps_reel f
    JOIN dwh.dim_point_mesure dp ON f.id_point_mesure = dp.id_point_mesure
    GROUP BY dp.id_pmac, dp.nom_point
    HAVING COUNT(DISTINCT f.canal) > 1
    ORDER BY nb_canaux DESC, dp.id_pmac
    LIMIT 15;
""")
print(df.to_string(index=False))


print("\n" + "=" * 80)
print("🎉 Vérifications Gold PMAC terminées")
print("=" * 80)