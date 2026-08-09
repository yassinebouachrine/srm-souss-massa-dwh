-- ═══════════════════════════════════════════════════════════════
-- DWH — DIM_CLIENT
-- Dimension clients GSTCOM
-- ═══════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS dwh.dim_client CASCADE;
CREATE TABLE dwh.dim_client (
    id_client                    BIGSERIAL PRIMARY KEY,
    
    -- ─── Clés métier ───
    police                       VARCHAR(20) UNIQUE NOT NULL,   -- Clé métier GSTCOM
    numero_compteur              VARCHAR(30),
    
    -- ─── Rattachement territorial (via loc_sec) ───
    id_loc_sec                   INTEGER REFERENCES dwh.dim_loc_sec(id_loc_sec),
    loc                          VARCHAR(20),
    sec                          VARCHAR(20),
    
    -- ─── Attributs métier ───
    type_part_adm                INTEGER,                       -- Type partenaire administratif
    tournee                      VARCHAR(20),                   -- TRN
    ordre_tournee                VARCHAR(20),                   -- ORD
    categorie                    VARCHAR(20),                   -- CAT (A, G, I, ...)
    
    -- ─── Nom/Adresse (anonymisés dans l'export) ───
    nom_client                   VARCHAR(200),
    adresse                      VARCHAR(500),
    
    -- ─── Géolocalisation ───
    latitude                     DECIMAL(12, 9),
    longitude                    DECIMAL(12, 9),
    
    -- ─── Compteur ───
    date_installation_compteur   DATE,
    age_compteur_annees          DECIMAL(6, 2),                 -- calculé : (today - date_installation) / 365.25
    matricule_lecteur            VARCHAR(30),
    
    -- ─── Flags métier ───
    est_gros_conso               BOOLEAN DEFAULT FALSE,         -- CAT='G' ou seuil conso
    statut_client                VARCHAR(30) DEFAULT 'ACTIF',   -- ACTIF | RESILIE | SUSPENDU
    
    -- ─── Traçabilité SCD Type 1 ───
    fichier_source_ref           VARCHAR(255),
    date_creation                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_modification            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dim_client_police       ON dwh.dim_client(police);
CREATE INDEX idx_dim_client_locsec       ON dwh.dim_client(id_loc_sec);
CREATE INDEX idx_dim_client_categorie    ON dwh.dim_client(categorie);
CREATE INDEX idx_dim_client_gros_conso   ON dwh.dim_client(est_gros_conso) 
                                          WHERE est_gros_conso = TRUE;
CREATE INDEX idx_dim_client_statut       ON dwh.dim_client(statut_client);

COMMENT ON TABLE dwh.dim_client IS 
    'Dimension clients GSTCOM (police + compteur + géolocalisation)';
COMMENT ON COLUMN dwh.dim_client.police IS 
    'N° police GSTCOM — clé métier unique';
COMMENT ON COLUMN dwh.dim_client.categorie IS 
    'Catégorie tarifaire GSTCOM : A (Particulier), G (Gros Conso), I (Industriel), etc.';
COMMENT ON COLUMN dwh.dim_client.age_compteur_annees IS 
    'Âge du compteur en années (calculé automatiquement lors de l''ETL)';

-- Client sentinelle (id=0) pour rejets/données orphelines
INSERT INTO dwh.dim_client 
    (id_client, police, categorie, statut_client, nom_client)
VALUES 
    (0, 'CLIENT_INCONNU', 'X', 'INCONNU', 'Client Non Renseigné')
ON CONFLICT (id_client) DO NOTHING;