-- ═══════════════════════════════════════════════════════════════
-- DWH — DIM_TYPE_ANOMALIE
-- Types d'anomalies de relève compteur GSTCOM
-- ═══════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS dwh.dim_type_anomalie CASCADE;
CREATE TABLE dwh.dim_type_anomalie (
    id_type_anomalie   INTEGER PRIMARY KEY,             -- ID manuel pour permettre id=0
    code_anomalie      VARCHAR(10) UNIQUE NOT NULL,     -- N, A, I, K, M, E, P...
    libelle_anomalie   VARCHAR(200) NOT NULL,
    categorie          VARCHAR(50),                     -- Releve_Normale | Compteur | Client
    gravite            INTEGER DEFAULT 1,               -- 1 (faible) → 5 (critique)
    est_bloquant       BOOLEAN DEFAULT FALSE,           -- TRUE si empêche la facturation normale
    date_creation      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dim_type_anomalie_categorie ON dwh.dim_type_anomalie(categorie);
CREATE INDEX idx_dim_type_anomalie_gravite   ON dwh.dim_type_anomalie(gravite);

COMMENT ON TABLE dwh.dim_type_anomalie IS 
    'Référentiel des types d''anomalies de relève compteur (codes AN_01/AN_02 GSTCOM)';