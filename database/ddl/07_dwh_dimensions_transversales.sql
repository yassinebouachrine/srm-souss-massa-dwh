-- ═══════════════════════════════════════════════════════════════
-- DWH — DIMENSIONS TRANSVERSALES (partagées entre Étoiles A, B, C)
--
-- Ces dimensions sont utilisées par plusieurs faits :
--   • DIM_ETAGE   : Étoiles A (Conso), B (Mesures), C (Rendement)
--   • DIM_SECTEUR : Étoiles A (Conso), B (Mesures), C (Rendement)
--
-- Pattern Kimball : "Conformed Dimensions"
-- ═══════════════════════════════════════════════════════════════


-- ─────────────────────────────────────────────────────────────
-- DIM_ETAGE
-- Étages hydrauliques (zones desservies par un même réservoir/cote)
-- Ex: TASSILA 75, BOUARGANE 130, MASSIRA 75, ANZA 70...
-- 
-- Le nombre à la fin du nom = cote d'altitude du réservoir (en m)
-- ─────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dwh.dim_etage CASCADE;
CREATE TABLE dwh.dim_etage (
    id_etage                INTEGER PRIMARY KEY,          -- ID manuel pour permettre id=0 (INCONNU)
    code_etage              VARCHAR(50) UNIQUE NOT NULL,
    nom_etage               VARCHAR(100) NOT NULL,
    type_etage              VARCHAR(50),                  -- Réservoir | Pompage | Distribution
    lineaire_km             DOUBLE PRECISION,             -- Longueur réseau (km)
    secteur_principal       VARCHAR(100),
    dp_responsable          VARCHAR(50),                  -- Code DP responsable
    nom_region              VARCHAR(100) DEFAULT 'Souss-Massa',
    nom_province            VARCHAR(100),
    nom_centre              VARCHAR(200),
    latitude                DECIMAL(10, 7),
    longitude               DECIMAL(10, 7),
    cote_altitude           DECIMAL(6, 2),                -- Altitude en mètres
    capacite_reservoir_m3   DOUBLE PRECISION,
    est_actif               BOOLEAN DEFAULT TRUE,
    date_creation           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dim_etage_nom      ON dwh.dim_etage(nom_etage);
CREATE INDEX idx_dim_etage_dp       ON dwh.dim_etage(dp_responsable);
CREATE INDEX idx_dim_etage_secteur  ON dwh.dim_etage(secteur_principal);

COMMENT ON TABLE dwh.dim_etage IS 
    'Étages hydrauliques (transversal Étoiles A, B, C). id_etage=0 = INCONNU';
COMMENT ON COLUMN dwh.dim_etage.cote_altitude IS 
    'Cote altitude du réservoir principal (nombre après le nom : "TASSILA 75" → 75m)';

-- Ligne sentinelle "INCONNU" (id=0) pour les faits sans étage rattaché
INSERT INTO dwh.dim_etage 
    (id_etage, code_etage, nom_etage, type_etage, nom_region, est_actif)
VALUES 
    (0, 'ETAGE_INCONNU', 'Étage Non Renseigné', 'Inconnu', 'Souss-Massa', TRUE);


-- ─────────────────────────────────────────────────────────────
-- DIM_SECTEUR
-- Secteurs hydrauliques (subdivisions plus fines qu'un étage)
-- Ex: ALHOUDA, TARRAST, DAKHLA, MASSIRA...
-- ─────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dwh.dim_secteur CASCADE;
CREATE TABLE dwh.dim_secteur (
    id_secteur              INTEGER PRIMARY KEY,          -- ID manuel pour permettre id=0
    code_secteur            VARCHAR(50) UNIQUE NOT NULL,
    nom_secteur             VARCHAR(100) NOT NULL,
    nom_secteur_hydraulique VARCHAR(200),                 -- Nom hydraulique détaillé
    lineaire_m              DOUBLE PRECISION,             -- Longueur en mètres
    nom_region              VARCHAR(100) DEFAULT 'Souss-Massa',
    nom_province            VARCHAR(100),
    nom_centre              VARCHAR(200),
    dp                      VARCHAR(50),                  -- Code DP
    est_actif               BOOLEAN DEFAULT TRUE,
    date_creation           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dim_secteur_nom       ON dwh.dim_secteur(nom_secteur);
CREATE INDEX idx_dim_secteur_dp        ON dwh.dim_secteur(dp);
CREATE INDEX idx_dim_secteur_province  ON dwh.dim_secteur(nom_province);

COMMENT ON TABLE dwh.dim_secteur IS 
    'Secteurs hydrauliques (transversal Étoiles A, B, C). id_secteur=0 = INCONNU';

-- Ligne sentinelle "INCONNU" (id=0)
INSERT INTO dwh.dim_secteur 
    (id_secteur, code_secteur, nom_secteur, nom_region, est_actif)
VALUES 
    (0, 'SECTEUR_INCONNU', 'Secteur Non Renseigné', 'Souss-Massa', TRUE);