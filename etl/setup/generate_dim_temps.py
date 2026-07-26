"""
Génère et peuple la table dwh.dim_temps.
Plage : 2020-01-01 → 2030-12-31
Exécution : python -m etl.setup.generate_dim_temps
"""
import pandas as pd
from etl.common.db import get_engine
from etl.common.logger import get_logger

logger = get_logger(__name__)

# Traduction française des noms de mois et jours
MOIS_FR = {
    1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre",
}
JOURS_FR = {
    0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi",
    4: "Vendredi", 5: "Samedi", 6: "Dimanche",
}

# Jours fériés au Maroc (fixes uniquement — les mobiles nécessiteraient une lib dédiée)
JOURS_FERIES_MAROC_FIXES = [
    (1, 1),    # Jour de l'an
    (1, 11),   # Manifeste de l'indépendance
    (5, 1),    # Fête du travail
    (7, 30),   # Fête du Trône
    (8, 14),   # Allégeance Oued Ed-Dahab
    (8, 20),   # Révolution du Roi et du Peuple
    (8, 21),   # Fête de la Jeunesse
    (11, 6),   # Marche verte
    (11, 18),  # Fête de l'indépendance
]


def generate_dim_temps(start: str = "2020-01-01", end: str = "2030-12-31") -> pd.DataFrame:
    """Génère le DataFrame de DIM_TEMPS."""
    dates = pd.date_range(start=start, end=end, freq="D")

    df = pd.DataFrame({"date_complete": dates})
    df["id_temps"] = df["date_complete"].dt.strftime("%Y%m%d").astype(int)
    df["jour"] = df["date_complete"].dt.day
    df["mois"] = df["date_complete"].dt.month
    df["nom_mois"] = df["mois"].map(MOIS_FR)
    df["trimestre"] = df["date_complete"].dt.quarter
    df["annee"] = df["date_complete"].dt.year
    df["jour_semaine"] = df["date_complete"].dt.dayofweek.map(JOURS_FR)
    df["est_weekend"] = df["date_complete"].dt.dayofweek.isin([5, 6])
    df["est_ferie"] = df.apply(
        lambda r: (r["mois"], r["jour"]) in JOURS_FERIES_MAROC_FIXES, axis=1
    )

    # Ordre des colonnes = ordre de la table
    df = df[[
        "id_temps", "date_complete", "jour", "mois", "nom_mois",
        "trimestre", "annee", "jour_semaine", "est_ferie", "est_weekend"
    ]]

    return df


def load_dim_temps(df: pd.DataFrame) -> None:
    """Charge le DataFrame dans dwh.dim_temps (truncate + insert)."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.exec_driver_sql("TRUNCATE TABLE dwh.dim_temps RESTART IDENTITY CASCADE;")
        df.to_sql(
            "dim_temps",
            conn,
            schema="dwh",
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )
    logger.info(f"✅ {len(df)} lignes chargées dans dwh.dim_temps")


def main():
    logger.info("🚀 Génération de DIM_TEMPS")
    df = generate_dim_temps("2020-01-01", "2030-12-31")
    logger.info(f"📅 {len(df)} dates générées ({df['date_complete'].min()} → {df['date_complete'].max()})")
    load_dim_temps(df)
    logger.info("🎉 DIM_TEMPS peuplée avec succès")


if __name__ == "__main__":
    main()