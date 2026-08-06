-- ═══════════════════════════════════════════════════════════════
-- DWH — BRIDGE_LOC_SEC_ETAGE
-- Table pont M:N entre Loc_Sec (GSTCOM) et Étage hydraulique
-- Gère la répartition avec pourcentages (ex: 50% ILLIGH + 50% HAY MOHAMMADI)
-- ═══════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS dwh.bridge_loc_sec_etage CASCADE;
CREATE TABLE dwh.bridge_loc_sec_etage (
    id_loc_sec       INTEGER NOT NULL REFERENCES dwh.dim_loc_sec(id_loc_sec),
    id_etage         INTEGER NOT NULL REFERENCES dwh.dim_etage(id_etage),
    pourcentage      DECIMAL(6,4) NOT NULL DEFAULT 1.0000,  -- 1.0000 = 100%, 0.5000 = 50%
    pct_effectif     DECIMAL(6,4),                          -- calculé (normalisation)
    date_creation    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id_loc_sec, id_etage)
);

CREATE INDEX idx_bridge_locsec ON dwh.bridge_loc_sec_etage(id_loc_sec);
CREATE INDEX idx_bridge_etage  ON dwh.bridge_loc_sec_etage(id_etage);

COMMENT ON TABLE dwh.bridge_loc_sec_etage IS 
    'Table pont M:N entre Loc_Sec et Étage avec pourcentage de répartition. Ex: 10_18 → 50% ILLIGH 175 + 50% HAY MOHAMMADI 210';
COMMENT ON COLUMN dwh.bridge_loc_sec_etage.pourcentage IS 
    'Pourcentage de la consommation à affecter à cet étage (0.0000 à 1.0000)';
COMMENT ON COLUMN dwh.bridge_loc_sec_etage.pct_effectif IS 
    'Pourcentage effectif après normalisation (somme par loc_sec = 1.0). Calculé automatiquement';