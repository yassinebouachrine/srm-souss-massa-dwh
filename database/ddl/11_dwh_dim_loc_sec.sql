-- ═══════════════════════════════════════════════════════════════
-- DWH — DIM_LOC_SEC
-- Dimension Localité + Secteur Commercial (GSTCOM)
-- Utilisée pour le rattachement client → étage via BRIDGE_LOC_SEC_ETAGE
-- ═══════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS dwh.dim_loc_sec CASCADE;
CREATE TABLE dwh.dim_loc_sec (
    id_loc_sec       INTEGER PRIMARY KEY,          -- ID manuel pour permettre id=0
    code_loc_sec     VARCHAR(50) UNIQUE NOT NULL,  -- "10_100"
    loc              VARCHAR(20) NOT NULL,          -- "10"
    secteur_com      VARCHAR(20) NOT NULL,          -- "100"
    loc_sec_norm     VARCHAR(50),                   -- version normalisée majuscule
    libelle_loc      VARCHAR(200),                  -- nom de la localité (optionnel)
    date_creation    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_loc_sec_loc     ON dwh.dim_loc_sec(loc);
CREATE INDEX idx_loc_sec_secteur ON dwh.dim_loc_sec(secteur_com);

COMMENT ON TABLE dwh.dim_loc_sec IS 
    'Dimension Localité + Secteur Commercial GSTCOM. Sert de clé de rattachement au réseau hydraulique via BRIDGE_LOC_SEC_ETAGE';

-- Ligne sentinelle (id=0) pour les clients sans loc_sec identifié
INSERT INTO dwh.dim_loc_sec 
    (id_loc_sec, code_loc_sec, loc, secteur_com, loc_sec_norm, libelle_loc)
VALUES 
    (0, 'LOCSEC_INCONNU', '0', '0', 'LOCSEC_INCONNU', 'Loc_Sec Non Renseigné')
ON CONFLICT (id_loc_sec) DO NOTHING;