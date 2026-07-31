-- ═══════════════════════════════════════════════════════════════
-- DWH — ÉTOILE B : Dimensions spécifiques aux Mesures Capteurs
--
-- Dimensions dédiées à l'Étoile B (Mesures Capteurs) :
--   • DIM_SOURCE_MESURE   : Systèmes d'origine (PMAC, PCWIN)
--   • DIM_POINT_MESURE    : Points physiques de mesure
--   • DIM_GROUPE_POINTS   : Groupes d'agrégation métier
--   • BRIDGE_GROUPE_POINT : Table pont many-to-many
-- ═══════════════════════════════════════════════════════════════


-- ─────────────────────────────────────────────────────────────
-- DIM_SOURCE_MESURE
-- Systèmes sources des mesures capteurs
-- ─────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dwh.dim_source_mesure CASCADE;
CREATE TABLE dwh.dim_source_mesure (
    id_source_mesure    SERIAL PRIMARY KEY,
    code_source         VARCHAR(30) UNIQUE NOT NULL,
    libelle_source      VARCHAR(200) NOT NULL,
    type_systeme        VARCHAR(50) NOT NULL,        -- CSV_FOLDER | SQL_SERVER
    description         TEXT,
    date_creation       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE dwh.dim_source_mesure IS 
    'Systèmes sources des mesures capteurs (PMAC live/archive, PCWIN SQL, etc.)';
COMMENT ON COLUMN dwh.dim_source_mesure.type_systeme IS 
    'Type technique : CSV_FOLDER (fichiers), SQL_SERVER (base), API_REST (web service)';


-- ─────────────────────────────────────────────────────────────
-- DIM_POINT_MESURE
-- Points physiques de mesure (unifié PMAC + PCWIN)
--
-- Convention id_pmac :
--   • PMAC     : "0007", "0416" (4 chiffres avec padding zéro)
--   • PCWIN    : "PCWIN_57"    (préfixe pour éviter les collisions)
--   • AGREGAT  : "AGREG_XXX"   (points virtuels calculés)
--
-- ⚠️ NOTE : Les attributs "étage" et "secteur" ne sont PAS ici.
-- Ils sont dans les tables DIM_ETAGE et DIM_SECTEUR (transversales).
-- Le lien se fait au niveau des tables de FAIT.
-- ─────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dwh.dim_point_mesure CASCADE;
CREATE TABLE dwh.dim_point_mesure (
    id_point_mesure         SERIAL PRIMARY KEY,
    
    -- ─── Identifiants ───
    id_pmac                 VARCHAR(20) UNIQUE NOT NULL,  -- Clé métier stable (respect schéma)
    id_source_mesure        INTEGER NOT NULL 
                            REFERENCES dwh.dim_source_mesure(id_source_mesure),
    
    -- ─── Attributs métier ───
    nom_point               VARCHAR(200) NOT NULL,        -- "07/AL HOUDA"
    station_pcwin           VARCHAR(200),                 -- Nom station PCWIN (si src=PCWIN)
    groupe_mesure           VARCHAR(100),                 -- "POINTS DE PRESSION" (respect schéma)
    
    -- ─── Localisation géographique ───
    latitude                DECIMAL(10, 7),
    longitude               DECIMAL(10, 7),
    cote_altitude           DECIMAL(6, 2),                -- Altitude du point (m)
    capacite_reservoir_m3   DOUBLE PRECISION,             -- Si point sur réservoir
    
    -- ─── Flags de capacité (booléens du schéma) ───
    est_pression            BOOLEAN DEFAULT FALSE,
    est_debit               BOOLEAN DEFAULT FALSE,
    est_reservoir           BOOLEAN DEFAULT FALSE,
    est_amont               BOOLEAN DEFAULT FALSE,
    est_aval                BOOLEAN DEFAULT FALSE,
    est_modulateur          BOOLEAN DEFAULT FALSE,
    
    -- ─── Attributs techniques ───
    canal_affichage         VARCHAR(50),                  -- "PRESSION_01", "DEBIT_02"
    code_voie               VARCHAR(20),                  -- "PRESSION"|"DEBIT"|"INDEX"
    
    -- ─── Traçabilité ───
    fichier_source_ref      VARCHAR(255),                 -- fichier référentiel d'origine
    est_actif               BOOLEAN DEFAULT TRUE,
    date_creation           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modification       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour requêtes analytiques
CREATE INDEX idx_dim_pt_source     ON dwh.dim_point_mesure(id_source_mesure);
CREATE INDEX idx_dim_pt_groupe     ON dwh.dim_point_mesure(groupe_mesure);
CREATE INDEX idx_dim_pt_canal      ON dwh.dim_point_mesure(canal_affichage);
CREATE INDEX idx_dim_pt_pression   ON dwh.dim_point_mesure(est_pression) 
                                    WHERE est_pression = TRUE;
CREATE INDEX idx_dim_pt_debit      ON dwh.dim_point_mesure(est_debit) 
                                    WHERE est_debit = TRUE;
CREATE INDEX idx_dim_pt_reservoir  ON dwh.dim_point_mesure(est_reservoir) 
                                    WHERE est_reservoir = TRUE;
CREATE INDEX idx_dim_pt_modulateur ON dwh.dim_point_mesure(est_modulateur) 
                                    WHERE est_modulateur = TRUE;

COMMENT ON TABLE dwh.dim_point_mesure IS 
    'Dimension unifiée des points de mesure (PMAC + PCWIN + agrégats)';
COMMENT ON COLUMN dwh.dim_point_mesure.id_pmac IS 
    'Identifiant naturel : "0007" (PMAC), "PCWIN_57" (PCWIN), "AGREG_XXX" (virtuel)';
COMMENT ON COLUMN dwh.dim_point_mesure.canal_affichage IS 
    'Canal détecté : PRESSION_01, DEBIT_02, INDEX_03 (utilisé pour KeyCanal)';
COMMENT ON COLUMN dwh.dim_point_mesure.groupe_mesure IS 
    'Catégorie : POINTS DE PRESSION, MODULATEURS, SECTEURS AGADIR/INEZGANE, SORTIES RESERVOIRS, GROS CONSO';


-- ─────────────────────────────────────────────────────────────
-- DIM_GROUPE_POINTS
-- Groupes d'agrégation métier (ex: "Somme GC ZI Ait Melloul")
-- ─────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dwh.dim_groupe_points CASCADE;
CREATE TABLE dwh.dim_groupe_points (
    id_groupe_points        SERIAL PRIMARY KEY,
    nom_groupe              VARCHAR(200) UNIQUE NOT NULL,
    description_groupe      TEXT,
    ordre_affichage         INTEGER DEFAULT 0,
    est_actif               BOOLEAN DEFAULT TRUE,
    date_creation           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE dwh.dim_groupe_points IS 
    'Groupes d''agrégation métier pour sommer plusieurs points ensemble';


-- ─────────────────────────────────────────────────────────────
-- BRIDGE_GROUPE_POINT
-- Table pont many-to-many entre groupes et points
-- ─────────────────────────────────────────────────────────────
DROP TABLE IF EXISTS dwh.bridge_groupe_point CASCADE;
CREATE TABLE dwh.bridge_groupe_point (
    id_groupe_points        INTEGER NOT NULL 
                            REFERENCES dwh.dim_groupe_points(id_groupe_points),
    id_point_mesure         INTEGER NOT NULL 
                            REFERENCES dwh.dim_point_mesure(id_point_mesure),
    coefficient             DECIMAL(6, 3) DEFAULT 1.0,    -- +1 (ajout), -1 (soustraction), 0.5 (pondération)
    ordre                   INTEGER DEFAULT 0,
    date_creation           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id_groupe_points, id_point_mesure)
);

CREATE INDEX idx_bridge_grp   ON dwh.bridge_groupe_point(id_groupe_points);
CREATE INDEX idx_bridge_point ON dwh.bridge_groupe_point(id_point_mesure);

COMMENT ON TABLE dwh.bridge_groupe_point IS 
    'Table pont : associe points à groupes avec coefficient';
COMMENT ON COLUMN dwh.bridge_groupe_point.coefficient IS 
    'Coefficient d''agrégation : +1 (addition), -1 (soustraction), 0.5 (pondération)';