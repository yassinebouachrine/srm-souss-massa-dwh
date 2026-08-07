"""Vérification du Gold Rendements."""
import pandas as pd
from etl.common.db import read_sql

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 240)


def section(t):
    print("\n" + "=" * 80)
    print(f"🔎 {t}")
    print("=" * 80)


# 1. Volumétrie
section("VOLUMÉTRIE FAIT_RENDEMENT_ETAGE")
df = read_sql("""
    SELECT source_donnees, COUNT(*) AS nb, 
           MIN(id_temps) AS temps_min, MAX(id_temps) AS temps_max
    FROM dwh.fait_rendement_etage
    GROUP BY source_donnees ORDER BY nb DESC;
""")
print(df.to_string(index=False))

# 2. Par étage
section("RÉPARTITION PAR ÉTAGE")
df = read_sql("""
    SELECT e.code_etage, e.nom_etage, COUNT(*) AS nb_mois,
           MIN(t.date_complete) AS mois_min,
           MAX(t.date_complete) AS mois_max,
           AVG(f.rendement)::DECIMAL(5,4) AS rendement_moyen
    FROM dwh.fait_rendement_etage f
    JOIN dwh.dim_etage e ON f.id_etage = e.id_etage
    JOIN dwh.dim_temps t ON f.id_temps = t.id_temps
    GROUP BY e.code_etage, e.nom_etage
    ORDER BY nb_mois DESC;
""")
print(df.to_string(index=False))


# 3. Dernier mois avec données complètes (histo+vol_amene)
section("DERNIER MOIS COMPLET - TOUS ÉTAGES")
df = read_sql("""
    WITH latest AS (
        SELECT MAX(id_temps) AS m 
        FROM dwh.fait_rendement_etage
        WHERE source_donnees = 'histo+vol_amene'
    )
    SELECT e.nom_etage,
           f.nb_clients,
           f.volume_amene::INT AS vol_amene,
           f.volume_facture::INT AS vol_facture,
           f.volume_pertes::INT AS vol_pertes,
           ROUND(f.rendement*100, 2) AS rendement_pct,
           ROUND(f.lineaire_km::numeric, 2) AS lineaire_km,
           ROUND(f.ilp::numeric, 3) AS ilp,
           f.source_donnees
    FROM dwh.fait_rendement_etage f
    JOIN dwh.dim_etage e ON f.id_etage = e.id_etage
    WHERE f.id_temps = (SELECT m FROM latest)
    ORDER BY f.volume_amene DESC;
""")
print(df.to_string(index=False))

# 4. Mois récents (mai 2025 → avril 2026) - vue synthèse
section("MOIS RÉCENTS - SYNTHÈSE")
df = read_sql("""
    SELECT 
        t.annee, t.mois, t.nom_mois,
        COUNT(DISTINCT f.id_etage) AS nb_etages,
        COUNT(*) FILTER (WHERE f.volume_facture IS NOT NULL) AS nb_avec_facture,
        COUNT(*) FILTER (WHERE f.volume_amene IS NOT NULL) AS nb_avec_amene,
        SUM(f.volume_amene)::BIGINT AS total_vol_amene,
        SUM(f.volume_facture)::BIGINT AS total_vol_facture
    FROM dwh.fait_rendement_etage f
    JOIN dwh.dim_temps t ON f.id_temps = t.id_temps
    WHERE t.annee >= 2025
    GROUP BY t.annee, t.mois, t.nom_mois
    ORDER BY t.annee DESC, t.mois DESC
    LIMIT 12;
""")
print(df.to_string(index=False))

# 4. Idempotence
section("TEST IDEMPOTENCE")
df = read_sql("""
    SELECT id_temps, id_etage, id_secteur, COUNT(*) AS nb
    FROM dwh.fait_rendement_etage
    GROUP BY id_temps, id_etage, id_secteur
    HAVING COUNT(*) > 1;
""")
print("✅ Aucun doublon" if df.empty else f"❌ {len(df)} doublons")

print("\n" + "=" * 80)