import sys
import io

# Force stdout en UTF-8 pour Windows PowerShell
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
from etl.common.db import read_sql





"""Vérification du Gold GSTCOM."""
import pandas as pd
from etl.common.db import read_sql

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 240)


def section(t):
    print("\n" + "=" * 80)
    print(f"🔎 {t}")
    print("=" * 80)


# 1. DIM_CLIENT
section("DIM_CLIENT - VOLUMÉTRIE")
df = read_sql("""
    SELECT 
        COUNT(*) AS nb_total,
        COUNT(*) FILTER (WHERE est_gros_conso) AS nb_gros_conso,
        COUNT(*) FILTER (WHERE id_loc_sec IS NOT NULL) AS nb_avec_locsec,
        COUNT(*) FILTER (WHERE latitude IS NOT NULL) AS nb_avec_gps,
        AVG(age_compteur_annees)::DECIMAL(6,2) AS age_moyen_compteur
    FROM dwh.dim_client
    WHERE id_client > 0;
""")
print(df.to_string(index=False))

# 2. Répartition par catégorie
section("RÉPARTITION PAR CATÉGORIE")
df = read_sql("""
    SELECT categorie, COUNT(*) AS nb
    FROM dwh.dim_client
    WHERE id_client > 0
    GROUP BY categorie ORDER BY nb DESC;
""")
print(df.to_string(index=False))

# 3. FAIT_CONSOMMATION
section("FAIT_CONSOMMATION - VOLUMÉTRIE")
df = read_sql("""
    SELECT 
        COUNT(*) AS nb_lignes,
        COUNT(DISTINCT id_client) AS nb_clients,
        COUNT(DISTINCT id_temps) AS nb_periodes,
        COUNT(DISTINCT id_etage) AS nb_etages,
        SUM(conso_facturee)::BIGINT AS total_conso_m3,
        AVG(conso_facturee)::DECIMAL(10,2) AS conso_moyenne_par_client
    FROM dwh.fait_consommation_client;
""")
print(df.to_string(index=False))

# 4. Conso par étage (dernier mois)
section("CONSOMMATION PAR ÉTAGE - DERNIER MOIS")
df = read_sql("""
    WITH latest AS (SELECT MAX(id_temps) AS m FROM dwh.fait_consommation_client)
    SELECT 
        e.nom_etage,
        COUNT(DISTINCT f.id_client) AS nb_clients,
        SUM(f.conso_facturee * f.pct_repartition_etage)::BIGINT AS vol_facture_pondere,
        AVG(f.pct_repartition_etage)::DECIMAL(5,4) AS pct_moyen
    FROM dwh.fait_consommation_client f
    JOIN dwh.dim_etage e ON f.id_etage = e.id_etage
    WHERE f.id_temps = (SELECT m FROM latest)
    GROUP BY e.nom_etage
    ORDER BY vol_facture_pondere DESC;
""")
print(df.to_string(index=False))

# 5. FAIT_ANOMALIE
section("FAIT_ANOMALIE - RÉPARTITION")
df = read_sql("""
    SELECT 
        ta.libelle_anomalie,
        COUNT(*) AS nb_occurences,
        COUNT(DISTINCT f.id_client) AS nb_clients_distincts
    FROM dwh.fait_anomalie_compteur f
    JOIN dwh.dim_type_anomalie ta ON f.id_type_anomalie = ta.id_type_anomalie
    GROUP BY ta.libelle_anomalie
    ORDER BY nb_occurences DESC;
""")
print(df.to_string(index=False))

# 6. Test idempotence
section("TEST IDEMPOTENCE")
df = read_sql("""
    SELECT id_client, id_temps, id_etage, COUNT(*) AS nb
    FROM dwh.fait_consommation_client
    GROUP BY id_client, id_temps, id_etage
    HAVING COUNT(*) > 1;
""")
print("✅ Aucun doublon conso" if df.empty else f"❌ {len(df)} doublons")

print("\n" + "=" * 80)