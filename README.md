# SRM Souss-Massa - Data Warehouse & BI

## Description

Systeme decisionnel complet pour la Societe Regionale Multiservices Souss-Massa.

Ce projet centralise:
- Indicateurs de performance des 6 Directions Provinciales
- Donnees capteurs multi-types (Debit, Pression, Index, Amount)
- Fichier clientele (Gstcom)
- Referentiels metier (Points de mesure, Groupes, Canaux)

## Architecture

- **Interface saisie**: Streamlit multi-pages (9 pages)
- **Prototypage ETL**: Jupyter Notebooks
- **Orchestration**: Apache Airflow
- **Base de donnees**: PostgreSQL 17 (architecture medaillon)
- **Visualisation**: Power BI

## Structure du Projet

- **database/**: Scripts SQL (DDL, DML, vues)
- **notebooks/**: Prototypage ETL en Jupyter (27 notebooks)
- **streamlit_app/**: Interface Streamlit
- **airflow_home/**: DAGs Airflow
- **etl/**: Code Python modulaire
- **dashboards/**: Rapports Power BI
- **data/**: Donnees locales (raw + processed)
- **tests/**: Tests unitaires et integration
- **scripts/**: Scripts utilitaires
- **docs/**: Documentation

## Data Warehouse

- **5 schemas**: staging, bronze, silver, gold, audit
- **17 dimensions** (dont 3 nouvelles pour capteurs)
- **5 tables de faits** (schema constellation)
- **2 tables d'agregats**
- **~50 tables au total**

## Workflow ETL

1. **Prototyper** dans notebooks/
2. **Refactorer** en modules etl/
3. **Orchestrer** avec des DAGs dans airflow_home/dags/

## Installation

Voir docs/02_installation.md

## Auteur

- **Developpeur**: BOUACHRINE Yassine
- **Periode**: Juillet - Aout 2026
- **Entreprise**: SRM Souss-Massa
