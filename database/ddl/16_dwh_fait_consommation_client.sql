-- ═══════════════════════════════════════════════════════════════
-- DWH — FAIT_CONSOMMATION_CLIENT
-- Fait de granularité : 1 client × 1 mois × 1 étage (via bridge)
--
-- Note importante :
-- Un client peut être rattaché à PLUSIEURS étages via BRIDGE_LOC_SEC_ETAGE
-- avec des pourcentages. Le fait stocke la consommation POUR CHAQUE étage,
-- pondérée par le pct_effectif.
-- Exemple : Client (loc=11, sec=18) → 50% ILLIGH 175 + 50% HAY MOHAMMADI 210
--          → 2 lignes de fait par mois
-- ═══════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS dwh.fait_consommation_client CASCADE;
CREATE TABLE dwh.fait_consommation_client (
    id_fait                  BIGSERIAL PRIMARY KEY,
    
    -- ─── Clés dimensions ───
    id_temps                 INTEGER NOT NULL REFERENCES dwh.dim_temps(id_temps),
    id_client                BIGINT NOT NULL REFERENCES dwh.dim_client(id_client),
    id_etage                 INTEGER NOT NULL DEFAULT 0 
                             REFERENCES dwh.dim_etage(id_etage),
    id_secteur               INTEGER NOT NULL DEFAULT 0 
                             REFERENCES dwh.dim_secteur(id_secteur),
    id_loc_sec               INTEGER REFERENCES dwh.dim_loc_sec(id_loc_sec),
    
    -- ─── Mesures brutes ───
    conso_reelle             DOUBLE PRECISION,      -- CONSO (m³)
    conso_facturee           DOUBLE PRECISION,      -- Conso facture
    conso_rapportee          DOUBLE PRECISION,      -- Conso_Rapportee_Mois (calculée)
    credit                   INTEGER,               -- CREDRES
    redressement             DOUBLE PRECISION,      -- REDRES
    
    -- ─── Index compteur ───
    index_debut              DOUBLE PRECISION,      -- idx_01
    index_fin                DOUBLE PRECISION,      -- IDX_02
    
    -- ─── Dates ───
    date_releve_debut        DATE,                  -- dt_rlv01
    date_releve_fin          DATE,                  -- dt_rlv02
    nb_jours_releve          INTEGER,               -- diff en jours
    
    -- ─── Répartition (bridge) ───
    pct_repartition_etage    DECIMAL(6, 4),         -- pct_effectif du bridge (1.0000, 0.5000...)
    
    -- ─── Traçabilité ───
    fichier_source           VARCHAR(255),
    date_chargement          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_fait_conso UNIQUE (id_client, id_temps, id_etage)
);

CREATE INDEX idx_fait_conso_temps   ON dwh.fait_consommation_client(id_temps);
CREATE INDEX idx_fait_conso_client  ON dwh.fait_consommation_client(id_client);
CREATE INDEX idx_fait_conso_etage   ON dwh.fait_consommation_client(id_etage);
CREATE INDEX idx_fait_conso_secteur ON dwh.fait_consommation_client(id_secteur);
CREATE INDEX idx_fait_conso_locsec  ON dwh.fait_consommation_client(id_loc_sec);

COMMENT ON TABLE dwh.fait_consommation_client IS 
    'Consommation mensuelle client, pondérée par étage via BRIDGE_LOC_SEC_ETAGE';
COMMENT ON COLUMN dwh.fait_consommation_client.pct_repartition_etage IS 
    'Pourcentage effectif de la consommation attribué à cet étage (bridge_loc_sec_etage.pct_effectif)';
COMMENT ON COLUMN dwh.fait_consommation_client.conso_rapportee IS 
    'Conso mensualisée = (index_fin - index_debut) * (30 / nb_jours_releve)';