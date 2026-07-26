# SRM Souss-Massa - Data Platform

Plateforme régionale de saisie, validation et gestion des données 
pour la Société Régionale Multiservices de Souss-Massa.

## État du projet

- **Partie 1 : Application Streamlit** — Terminée
  - Authentification sécurisée avec bcrypt
  - Saisie des indicateurs de performance DP
  - Saisie des réclamations
  - Workflow de validation à 3 niveaux (Agent → Admin DP → Admin Régional)
  - Traçabilité complète des corrections

- **Partie 2 : Pipeline ETL** — À venir
  - Extraction des données (PMAC, PCWIN, GSTCOM, référentiels)
  - Transformation et nettoyage
  - Chargement dans le Data Warehouse
  - Orchestration avec Airflow

- **Partie 3 : Data Warehouse & Power BI** — À venir
  - Modèle en constellation
  - Dashboards Power BI

## Installation

### Prérequis

- Python 3.10+
- PostgreSQL 17
- Windows 10/11

### Étapes

```bash
# 1. Cloner le projet
git clone <url>
cd srm-souss-massa-dwh

# 2. Créer l'environnement virtuel
python -m venv venv
venv\Scripts\activate

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer .env
copy .env.example .env
# Éditer .env avec vos identifiants PostgreSQL

# 5. Créer la base de données
psql -h localhost -U postgres -c "CREATE DATABASE srm_datawarehouse;"

# 6. Initialiser les tables
cd streamlit_app
python scripts\init_database.py

# 7. Créer les utilisateurs
python scripts\init_passwords.py

# 8. Lancer l'application
streamlit run app.py