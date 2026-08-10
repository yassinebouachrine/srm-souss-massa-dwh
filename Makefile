# ═══════════════════════════════════════════════════════════════
# SRM Souss-Massa DWH — Makefile
# Commandes standardisées pour développement et production
# ═══════════════════════════════════════════════════════════════

.PHONY: help install init-db reset run-all run-pmac run-pcwin \
        run-excel run-streamlit run-gstcom run-rendements \
        check-all clean venv test docs

# Couleurs
GREEN  := \033[0;32m
YELLOW := \033[0;33m
NC     := \033[0m

# Python et pip
PYTHON := python
PIP    := pip

# ═══════════════════════════════════════════════════════════════
# AIDE
# ═══════════════════════════════════════════════════════════════

help:
	@echo "$(GREEN)═══════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)SRM Souss-Massa DWH - Commandes disponibles$(NC)"
	@echo "$(GREEN)═══════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)📦 Installation :$(NC)"
	@echo "  make install         Installe les dépendances Python"
	@echo "  make venv            Crée un environnement virtuel"
	@echo ""
	@echo "$(YELLOW)🔧 Base de données :$(NC)"
	@echo "  make init-db         Initialise la base (DDL + DML + seeds)"
	@echo "  make init-db-ddl     DDL uniquement"
	@echo "  make reset           Réinitialise complètement la DB (DANGER)"
	@echo ""
	@echo "$(YELLOW)🚀 Pipelines ETL :$(NC)"
	@echo "  make run-all         Exécute tous les pipelines"
	@echo "  make run-excel       Pipeline Indicateurs Excel"
	@echo "  make run-streamlit   Pipeline Streamlit"
	@echo "  make run-pmac        Pipeline PMAC (capteurs CSV)"
	@echo "  make run-pcwin       Pipeline PCWIN (SQL Server)"
	@echo "  make run-rendements  Pipeline Rendements"
	@echo "  make run-gstcom      Pipeline GSTCOM (clientèle)"
	@echo ""
	@echo "$(YELLOW)✅ Vérifications :$(NC)"
	@echo "  make check-all       Lance tous les checks de qualité"
	@echo ""
	@echo "$(YELLOW)🧹 Maintenance :$(NC)"
	@echo "  make clean           Nettoie __pycache__, logs anciens"
	@echo "  make docs            Génère la documentation"

# ═══════════════════════════════════════════════════════════════
# INSTALLATION
# ═══════════════════════════════════════════════════════════════

venv:
	$(PYTHON) -m venv venv
	@echo "$(GREEN)✅ venv créé. Activer avec : venv\\Scripts\\activate (Windows) ou source venv/bin/activate (Linux)$(NC)"

install:
	$(PIP) install --upgrade pip
	$(PIP) install "numpy==1.26.3"
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)✅ Dépendances installées$(NC)"

# ═══════════════════════════════════════════════════════════════
# BASE DE DONNÉES
# ═══════════════════════════════════════════════════════════════

init-db:
	$(PYTHON) scripts/init_database.py

init-db-ddl:
	$(PYTHON) scripts/init_database.py --ddl-only

init-db-seeds:
	$(PYTHON) scripts/init_database.py --seeds-only

reset:
	@echo "$(YELLOW)⚠️  ATTENTION : Cela va DROP et recréer la base ! Ctrl+C pour annuler...$(NC)"
	@timeout /t 5 /nobreak 2>nul || sleep 5
	psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS srm_datawarehouse;"
	psql -h localhost -U postgres -c "CREATE DATABASE srm_datawarehouse;"
	$(MAKE) init-db

# ═══════════════════════════════════════════════════════════════
# PIPELINES ETL
# ═══════════════════════════════════════════════════════════════

run-all:
	$(PYTHON) scripts/run_full_pipeline.py

run-excel:
	$(PYTHON) scripts/run_full_pipeline.py --source indicateurs_reclamations

run-streamlit:
	$(PYTHON) scripts/run_full_pipeline.py --source streamlit

run-pmac:
	$(PYTHON) scripts/run_full_pipeline.py --source pmac

run-pcwin:
	$(PYTHON) scripts/run_full_pipeline.py --source pcwin

run-rendements:
	$(PYTHON) scripts/run_full_pipeline.py --source rendements

run-gstcom:
	$(PYTHON) scripts/run_full_pipeline.py --source gstcom

# ═══════════════════════════════════════════════════════════════
# CHECKS
# ═══════════════════════════════════════════════════════════════

check-all:
	$(PYTHON) scripts/run_full_pipeline.py --checks-only

# ═══════════════════════════════════════════════════════════════
# MAINTENANCE
# ═══════════════════════════════════════════════════════════════

clean:
	@echo "$(YELLOW)🧹 Nettoyage...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>nul || rmdir /s /q __pycache__ 2>nul || echo ""
	find . -type f -name "*.pyc" -delete 2>nul || del /s /q *.pyc 2>nul || echo ""
	@echo "$(GREEN)✅ Nettoyage terminé$(NC)"

docs:
	@echo "$(YELLOW)📖 Génération de la documentation...$(NC)"
	@echo "TODO : Sphinx ou MkDocs"