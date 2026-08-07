"""Vérification du Gold après chargement DWH."""
import pandas as pd
from etl.common.db import read_sql

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 220)


def section(title: str):
    print("\n" + "=" * 80)
    print(f"🔎 {title}")
    print("=" * 80)


# ═══ 1. VOLUMÉTRIE GLOBALE ═══
section("VOLUMÉTRIE DWH")
df = read_sql("""
    SELECT 'fait_indicateurs_performance_dp' AS table_name, COUNT(*) AS nb_lignes
    FROM dwh.fait_indicateurs_performance_dp
    UNION ALL
    SELECT 'fait_reclamation', COUNT(*)
    FROM dwh.fait_reclamation
    UNION ALL
    SELECT 'dim_temps', COUNT(*) FROM dwh.dim_temps
    UNION ALL
    SELECT 'dim_dp', COUNT(*) FROM dwh.dim_dp
    UNION ALL
    SELECT 'dim_centre', COUNT(*) FROM dwh.dim_centre
    UNION ALL
    SELECT 'dim_type_indicateur_dp', COUNT(*) FROM dwh.dim_type_indicateur_dp
    UNION ALL
    SELECT 'dim_type_reclamation', COUNT(*) FROM dwh.dim_type_reclamation
    ORDER BY table_name;
""")
print(df.to_string(index=False))


# ═══ 2. RÉPARTITION INDICATEURS PAR DP ═══
section("INDICATEURS - Répartition par DP")
df = read_sql("""
    SELECT d.code_dp, d.nom_dp, COUNT(*) AS nb_faits,
           COUNT(DISTINCT f.id_centre) AS nb_centres,
           COUNT(DISTINCT f.id_temps) AS nb_periodes
    FROM dwh.fait_indicateurs_performance_dp f
    JOIN dwh.dim_dp d ON f.id_dp = d.id_dp
    GROUP BY d.code_dp, d.nom_dp
    ORDER BY d.code_dp;
""")
print(df.to_string(index=False))


# ═══ 3. RÉPARTITION PAR SOURCE ═══
section("RÉPARTITION PAR SOURCE (excel_legacy vs streamlit)")
df = read_sql("""
    SELECT 'indicateurs' AS domaine, source_saisie, COUNT(*) AS nb
    FROM dwh.fait_indicateurs_performance_dp
    GROUP BY source_saisie
    UNION ALL
    SELECT 'reclamations', source_saisie, COUNT(*)
    FROM dwh.fait_reclamation
    GROUP BY source_saisie
    ORDER BY domaine, source_saisie;
""")
print(df.to_string(index=False))


# ═══ 4. TOP 10 INDICATEURS ═══
section("TOP 10 INDICATEURS (nb de faits)")
df = read_sql("""
    SELECT ti.code_indicateur, ti.libelle_indicateur, ti.unite,
           COUNT(*) AS nb_faits
    FROM dwh.fait_indicateurs_performance_dp f
    JOIN dwh.dim_type_indicateur_dp ti ON f.id_type_indicateur = ti.id_type_indicateur
    GROUP BY ti.code_indicateur, ti.libelle_indicateur, ti.unite
    ORDER BY nb_faits DESC
    LIMIT 10;
""")
print(df.to_string(index=False))


# ═══ 5. AGRÉGATION DP vs CENTRES ═══
section("AGRÉGATION DP (id_centre=0) vs CENTRES RÉELS")
df = read_sql("""
    SELECT 
        CASE WHEN f.id_centre = 0 THEN 'Recap DP (agrégation)' ELSE 'Centres réels' END AS type_ligne,
        COUNT(*) AS nb_faits
    FROM dwh.fait_indicateurs_performance_dp f
    GROUP BY (f.id_centre = 0)
    ORDER BY type_ligne;
""")
print(df.to_string(index=False))


# ═══ 6. EXEMPLE DE FAITS RÉCLAMATIONS ═══
section("ÉCHANTILLON RÉCLAMATIONS (10 lignes)")
df = read_sql("""
    SELECT 
        t.annee, t.mois,
        d.code_dp,
        c.code_centre,
        tr.code, tr.libelle,
        f.nb_reclamations,
        f.temps_moyen_coupure,
        f.delai_moyen_traitement,
        f.source_saisie
    FROM dwh.fait_reclamation f
    JOIN dwh.dim_temps t              ON f.id_temps = t.id_temps
    JOIN dwh.dim_dp d                 ON f.id_dp = d.id_dp
    LEFT JOIN dwh.dim_centre c        ON f.id_centre = c.id_centre
    JOIN dwh.dim_type_reclamation tr  ON f.id_type = tr.id_type
    ORDER BY f.id_fait
    LIMIT 10;
""")
print(df.to_string(index=False))


# ═══ 7. RÉCLAMATIONS PAR TYPE (avec ventilation nb / durée) ═══
section("RÉCLAMATIONS - Ventilation par type")
df = read_sql("""
    SELECT 
        tr.code, tr.libelle, tr.categorie,
        COUNT(*) AS nb_faits,
        SUM(CASE WHEN f.nb_reclamations        IS NOT NULL THEN 1 ELSE 0 END) AS n_avec_nb,
        SUM(CASE WHEN f.temps_moyen_coupure    IS NOT NULL THEN 1 ELSE 0 END) AS n_avec_temps,
        SUM(CASE WHEN f.delai_moyen_traitement IS NOT NULL THEN 1 ELSE 0 END) AS n_avec_delai
    FROM dwh.fait_reclamation f
    JOIN dwh.dim_type_reclamation tr ON f.id_type = tr.id_type
    GROUP BY tr.code, tr.libelle, tr.categorie
    ORDER BY nb_faits DESC;
""")
print(df.to_string(index=False))


# ═══ 8. PÉRIODES CHARGÉES ═══
section("PÉRIODES CHARGÉES")
df = read_sql("""
    SELECT t.annee, t.mois, t.nom_mois, COUNT(*) AS nb_faits
    FROM dwh.fait_indicateurs_performance_dp f
    JOIN dwh.dim_temps t ON f.id_temps = t.id_temps
    GROUP BY t.annee, t.mois, t.nom_mois
    ORDER BY t.annee, t.mois;
""")
print(df.to_string(index=False))


# ═══ 9. TEST D'IDEMPOTENCE ═══
section("TEST IDEMPOTENCE - Doublons ? (doit être vide)")
df = read_sql("""
    SELECT id_temps, id_dp, id_centre, id_type_indicateur, source_saisie, COUNT(*) AS nb
    FROM dwh.fait_indicateurs_performance_dp
    GROUP BY id_temps, id_dp, id_centre, id_type_indicateur, source_saisie
    HAVING COUNT(*) > 1;
""")
if df.empty:
    print("✅ Aucun doublon — contrainte unique OK")
else:
    print(f"❌ {len(df)} doublons détectés !")
    print(df.head())

print("\n" + "=" * 80)
print("🎉 Vérifications terminées")
print("=" * 80)