"""Vérification du Gold après chargement DWH (avec focus source_saisie)."""
import pandas as pd
from etl.common.db import read_sql

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 220)


def section(title: str):
    print("\n" + "=" * 80)
    print(f"🔎 {title}")
    print("=" * 80)


# ═══ 1. VOLUMÉTRIE PAR SOURCE ═══
section("VOLUMÉTRIE PAR source_saisie")
df = read_sql("""
    SELECT 'indicateurs' AS domaine, source_saisie, COUNT(*) AS nb_lignes
    FROM dwh.fait_indicateurs_performance_dp
    GROUP BY source_saisie
    UNION ALL
    SELECT 'reclamations', source_saisie, COUNT(*)
    FROM dwh.fait_reclamation
    GROUP BY source_saisie
    ORDER BY domaine, source_saisie;
""")
print(df.to_string(index=False))


# ═══ 2. RÉCLAMATIONS PERSONNALISÉES CRÉÉES ═══
section("RÉCLAMATIONS PERSONNALISÉES (est_personnalisee=TRUE)")
df = read_sql("""
    SELECT id_type, code, libelle, categorie, date_creation
    FROM dwh.dim_type_reclamation
    WHERE est_personnalisee = TRUE
    ORDER BY id_type;
""")
if df.empty:
    print("(Aucune)")
else:
    print(df.to_string(index=False))


# ═══ 3. FAITS STREAMLIT INDICATEURS ═══
section("FAITS STREAMLIT - INDICATEURS (détail)")
df = read_sql("""
    SELECT 
        t.annee, t.mois,
        d.code_dp,
        c.code_centre, c.nom_centre,
        ti.code_indicateur, ti.libelle_indicateur, ti.unite,
        f.valeur,
        f.fichier_source AS source_table,
        f.onglet_source  AS lot_id
    FROM dwh.fait_indicateurs_performance_dp f
    JOIN dwh.dim_temps t                     ON f.id_temps = t.id_temps
    JOIN dwh.dim_dp d                        ON f.id_dp = d.id_dp
    JOIN dwh.dim_centre c                    ON f.id_centre = c.id_centre
    JOIN dwh.dim_type_indicateur_dp ti       ON f.id_type_indicateur = ti.id_type_indicateur
    WHERE f.source_saisie = 'streamlit'
    ORDER BY t.annee, t.mois, d.code_dp, ti.code_indicateur;
""")
print(df.to_string(index=False))


# ═══ 4. FAITS STREAMLIT RÉCLAMATIONS ═══
section("FAITS STREAMLIT - RÉCLAMATIONS (détail)")
df = read_sql("""
    SELECT 
        t.annee, t.mois,
        d.code_dp,
        c.code_centre,
        tr.code, tr.libelle, tr.est_personnalisee,
        f.nb_reclamations,
        f.temps_moyen_coupure,
        f.delai_moyen_traitement,
        f.onglet_source AS lot_id
    FROM dwh.fait_reclamation f
    JOIN dwh.dim_temps t                ON f.id_temps = t.id_temps
    JOIN dwh.dim_dp d                   ON f.id_dp = d.id_dp
    JOIN dwh.dim_centre c               ON f.id_centre = c.id_centre
    JOIN dwh.dim_type_reclamation tr    ON f.id_type = tr.id_type
    WHERE f.source_saisie = 'streamlit'
    ORDER BY t.annee, t.mois, d.code_dp, tr.code;
""")
print(df.to_string(index=False))


# ═══ 5. TEST IDEMPOTENCE ═══
section("TEST IDEMPOTENCE - Doublons ? (doit être vide)")
df = read_sql("""
    SELECT id_temps, id_dp, id_centre, id_type_indicateur, source_saisie, COUNT(*) AS nb
    FROM dwh.fait_indicateurs_performance_dp
    GROUP BY id_temps, id_dp, id_centre, id_type_indicateur, source_saisie
    HAVING COUNT(*) > 1;
""")
if df.empty:
    print("✅ Aucun doublon indicateurs")
else:
    print(f"❌ {len(df)} doublons indicateurs !")
    print(df.head())

df = read_sql("""
    SELECT id_temps, id_dp, id_centre, id_type, source_saisie, COUNT(*) AS nb
    FROM dwh.fait_reclamation
    GROUP BY id_temps, id_dp, id_centre, id_type, source_saisie
    HAVING COUNT(*) > 1;
""")
if df.empty:
    print("✅ Aucun doublon réclamations")
else:
    print(f"❌ {len(df)} doublons réclamations !")
    print(df.head())


# ═══ 6. COMPARAISON EXCEL vs STREAMLIT ═══
section("COMPARAISON EXCEL_LEGACY vs STREAMLIT")
df = read_sql("""
    WITH stats AS (
        SELECT source_saisie, COUNT(*) AS nb_faits,
               COUNT(DISTINCT id_dp) AS nb_dp,
               COUNT(DISTINCT id_centre) AS nb_centres,
               COUNT(DISTINCT id_temps) AS nb_periodes
        FROM dwh.fait_indicateurs_performance_dp
        GROUP BY source_saisie
    )
    SELECT * FROM stats ORDER BY source_saisie;
""")
print("📊 Indicateurs :")
print(df.to_string(index=False))


print("\n" + "=" * 80)
print("🎉 Vérifications terminées")
print("=" * 80)