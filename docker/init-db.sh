#!/bin/bash
set -e

# Création des utilisateurs et bases de données
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
	CREATE USER airflow WITH PASSWORD 'airflow';
	CREATE DATABASE airflow;
	GRANT ALL PRIVILEGES ON DATABASE airflow TO airflow;
    ALTER DATABASE airflow OWNER TO airflow;
    
	CREATE DATABASE srm_datawarehouse;
	GRANT ALL PRIVILEGES ON DATABASE srm_datawarehouse TO srm_admin;
EOSQL