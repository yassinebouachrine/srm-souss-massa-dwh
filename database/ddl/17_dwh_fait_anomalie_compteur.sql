-- ═══════════════════════════════════════════════════════════════
-- DWH — FAIT_ANOMALIE_COMPTEUR
-- Fait de granularité : 1 client × 1 mois × 1 type d'anomalie
-- 
-- Alimenté depuis le champ AN_02 de GSTCOM
-- (uniquement les anomalies non-normales, code ≠ 'N')
-- ═══════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS dwh.fait_anomalie_compteur CASCADE;
CREATE TABLE dwh.fait_anomalie_compteur (
    id_fait               BIGSERIAL PRIMARY KEY,
    
    -- ─── Clés dimensions ───
    id_temps              INTEGER NOT NULL REFERENCES dwh.dim_temps(id_temps),
    id_client             BIGINT NOT NULL REFERENCES dwh.dim_client(id_client),
    id_etage              INTEGER NOT NULL DEFAULT 0 
                          REFERENCES dwh.dim_etage(id_etage),
    id_secteur            INTEGER NOT NULL DEFAULT 0 
                          REFERENCES dwh.dim_secteur(id_secteur),
    id_type_anomalie      INTEGER NOT NULL 
                          REFERENCES dwh.dim_type_anomalie(id_type_anomalie),
    
    -- ─── Mesures ───
    nb_anomalies          INTEGER DEFAULT 1,        -- Compteur (=1 par ligne, sommable)
    nb_clients_affectes   INTEGER DEFAULT 1,        -- Distinct count agrégé
    
    -- ─── Contexte ───
    date_releve           DATE,                     -- dt_rlv02
    pct_repartition_etage DECIMAL(6, 4),
    
    -- ─── Traçabilité ───
    fichier_source        VARCHAR(255),
    date_chargement       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_fait_anomalie UNIQUE (id_client, id_temps, id_etage, id_type_anomalie)
);

CREATE INDEX idx_fait_anomalie_temps    ON dwh.fait_anomalie_compteur(id_temps);
CREATE INDEX idx_fait_anomalie_client   ON dwh.fait_anomalie_compteur(id_client);
CREATE INDEX idx_fait_anomalie_etage    ON dwh.fait_anomalie_compteur(id_etage);
CREATE INDEX idx_fait_anomalie_type     ON dwh.fait_anomalie_compteur(id_type_anomalie);

COMMENT ON TABLE dwh.fait_anomalie_compteur IS 
    'Anomalies de relève compteur (issues du champ AN_02 de GSTCOM)';