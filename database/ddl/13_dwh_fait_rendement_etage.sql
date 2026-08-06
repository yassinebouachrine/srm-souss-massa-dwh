-- ═══════════════════════════════════════════════════════════════
-- DWH — FAIT_RENDEMENT_ETAGE
-- Fait mensuel : rendement par étage hydraulique
-- Fusion des sources : histo_pbi + vol_amene + calculs dérivés
-- ═══════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS dwh.fait_rendement_etage CASCADE;
CREATE TABLE dwh.fait_rendement_etage (
    id_fait                 BIGSERIAL PRIMARY KEY,
    
    -- ─── Clés dimensions ───
    id_temps                INTEGER NOT NULL REFERENCES dwh.dim_temps(id_temps),
    id_etage                INTEGER NOT NULL REFERENCES dwh.dim_etage(id_etage),
    id_secteur              INTEGER NOT NULL DEFAULT 0 
                            REFERENCES dwh.dim_secteur(id_secteur),
    
    -- ─── Volumes ───
    volume_amene            DOUBLE PRECISION,      -- m³ apportés dans l'étage
    volume_facture          DOUBLE PRECISION,      -- m³ facturés aux clients
    volume_pertes           DOUBLE PRECISION,      -- calculé : amene - facture
    volume_facture_ebo      DOUBLE PRECISION,      -- ventes en gros (Ex-RAMSA)
    volume_amene_ramsa      DOUBLE PRECISION,      -- apport RAMSA
    
    -- ─── Métriques clients ───
    nb_clients              INTEGER,
    age_compteur_moyen      DECIMAL(6,2),          -- en années
    nb_jours_moyen_releve   DECIMAL(5,2),
    
    -- ─── Rendements ───
    rendement               DECIMAL(6,4),          -- 0.7549 = 75.49%
    rendement_off           DECIMAL(6,4),          -- rendement officiel
    pseudo_rendement        DECIMAL(6,4),          -- pseudo-rendement (débit min)
    
    -- ─── ILP (Indice Linéaire de Perte) ───
    lineaire_km             DOUBLE PRECISION,      -- copie du linéaire pour perf PBI
    ilp                     DOUBLE PRECISION,      -- volume_pertes / lineaire_km / nb_jours
    
    -- ─── Traçabilité ───
    source_donnees          VARCHAR(50),           -- 'histo_pbi+vol_amene', 'calcule', etc.
    fichier_source          VARCHAR(255),
    date_chargement         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_fait_rendement UNIQUE (id_temps, id_etage, id_secteur)
);

CREATE INDEX idx_fait_rend_temps   ON dwh.fait_rendement_etage(id_temps);
CREATE INDEX idx_fait_rend_etage   ON dwh.fait_rendement_etage(id_etage);
CREATE INDEX idx_fait_rend_secteur ON dwh.fait_rendement_etage(id_secteur);

COMMENT ON TABLE dwh.fait_rendement_etage IS 
    'Fait mensuel : rendement, volumes et ILP par étage hydraulique. Alimenté par fusion histo_pbi + vol_amene';
COMMENT ON COLUMN dwh.fait_rendement_etage.rendement IS 
    'Rendement = volume_facture / volume_amene (0.0000 à 1.0000, valeurs >1 possibles pour anomalies)';
COMMENT ON COLUMN dwh.fait_rendement_etage.ilp IS 
    'Indice Linéaire de Perte = volume_pertes / lineaire_km / nb_jours (m³/km/j)';
COMMENT ON COLUMN dwh.fait_rendement_etage.id_secteur IS 
    'Utiliser 0 (SECTEUR_INCONNU) pour les rendements agrégés au niveau étage';