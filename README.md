#  SRM Souss-Massa - Data Platform

Plateforme régionale de collecte, traitement et visualisation des données 
hydrauliques pour la **Société Régionale Multiservices de Souss-Massa**.

![Status](https://img.shields.io/badge/status-production--ready-green)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![PostgreSQL](https://img.shields.io/badge/postgresql-17-blue)

---

##  Description

Cette plateforme centralise **6 sources de données** dans un Data Warehouse en 
**constellation Kimball**, orchestré par Airflow et visualisé via Power BI.

### Sources de données

| Source | Type | Fréquence |
|--------|------|-----------|
| **Excel Indicateurs DP** | Fichiers OneDrive | Mensuel |
| **Streamlit App** | PostgreSQL app_staging | Continu |
| **PMAC** | CSV capteurs (Live + Archive) | Journalier |
| **PCWIN** | SQL Server ScadaNetDb | Journalier |
| **Rendements** | Excel référentiels | Mensuel |
| **GSTCOM** | Excel clientèle | Mensuel |

### Modèle en constellation

- **Étoile A** : Consommation & Anomalies clients (GSTCOM)
- **Étoile B** : Mesures Capteurs (temps réel, journalier, période)
- **Étoile C** : Rendement par étage hydraulique
- **Étoile D** : Performance DP & Réclamations

---

##  Architecture
┌─────────────────┐
│ Sources Data │ Excel · CSV · SQL Server · PostgreSQL
└────────┬────────┘
│
┌────▼─────┐
│ BRONZE │ Extract brut → Parquet
└────┬─────┘
│
┌────▼─────┐
│ SILVER │ Transform, validate, dedupe
└────┬─────┘
│
┌────▼─────┐
│ GOLD │ Load DWH PostgreSQL
└────┬─────┘
│
┌────▼─────┐
│ POWER BI │ Dashboards temps réel
└──────────┘

---

##  Installation

### Prérequis

- Python 3.10+
- PostgreSQL 17
- Windows 10/11 ou Linux (Ubuntu 22.04+)
- (Optionnel) Docker & Docker Compose

### Installation locale

```bash
# 1. Cloner le projet
git clone <URL_REPO>
cd srm-souss-massa-dwh

# 2. Créer l'environnement virtuel
python -m venv venv
venv\Scripts\activate           # Windows
# source venv/bin/activate      # Linux

# 3. Installer les dépendances
make install
# ou : pip install -r requirements.txt

# 4. Configurer les variables d'environnement
copy .env.example .env
# Éditer .env avec vos identifiants

# 5. Créer et initialiser la base
psql -U postgres -c "CREATE DATABASE srm_datawarehouse;"
make init-db

# 6. Lancer les pipelines
make run-all

# 7. Vérifier les résultats
make check-all
