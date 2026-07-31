-- ═══════════════════════════════════════════════════════════════
-- SEED — DIM_SOURCE_MESURE
-- Systèmes sources des mesures capteurs
-- ═══════════════════════════════════════════════════════════════

TRUNCATE TABLE dwh.dim_source_mesure RESTART IDENTITY CASCADE;

INSERT INTO dwh.dim_source_mesure 
    (code_source, libelle_source, type_systeme, description)
VALUES
    ('PMAC_LIVE',    
     'PMAC Fichiers Live', 
     'CSV_FOLDER',
     'Fichiers CSV live générés par les enregistreurs PMAC. Dossier de collecte : \\192.168.1.41\Export'),
    
    ('PMAC_ARCHIVE', 
     'PMAC Fichiers Archive', 
     'CSV_FOLDER',
     'Archive historique des fichiers CSV PMAC. Dossier : D:\ARCHIVE_EXPORT'),
    
    ('PCWIN',        
     'PCWIN Scada SQL Server', 
     'SQL_SERVER',
     'Base SQL Server ScadaNetDb — tables internal_numeric_archives + NumericInformations + Stations');

-- Vérification
SELECT * FROM dwh.dim_source_mesure ORDER BY id_source_mesure;