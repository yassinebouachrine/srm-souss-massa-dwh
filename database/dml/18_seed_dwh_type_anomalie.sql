-- ═══════════════════════════════════════════════════════════════
-- SEED — DIM_TYPE_ANOMALIE
-- Codes anomalies GSTCOM (à ajuster selon la vraie table de référence)
-- ═══════════════════════════════════════════════════════════════

-- Sentinel "INCONNU" (id=0)
INSERT INTO dwh.dim_type_anomalie 
    (id_type_anomalie, code_anomalie, libelle_anomalie, categorie, gravite, est_bloquant)
VALUES
    (0, 'INCONNU', 'Anomalie Non Renseignée', 'Autre', 0, FALSE),
    
    -- Relève normale
    (1, 'N', 'Relève normale',                    'Releve_Normale', 1, FALSE),
    
    -- Anomalies client
    (2, 'A', 'Client absent',                     'Client',         2, FALSE),
    
    -- Anomalies compteur
    (3, 'I', 'Compteur inaccessible',             'Compteur',       3, TRUE),
    (4, 'K', 'Compteur bloqué',                   'Compteur',       4, TRUE),
    (5, 'M', 'Compteur changé/modifié',           'Compteur',       2, FALSE),
    (6, 'E', 'Compteur à l''envers (inversé)',    'Compteur',       4, TRUE),
    (7, 'P', 'Compteur en panne',                 'Compteur',       5, TRUE)

ON CONFLICT (id_type_anomalie) DO UPDATE
SET code_anomalie    = EXCLUDED.code_anomalie,
    libelle_anomalie = EXCLUDED.libelle_anomalie,
    categorie        = EXCLUDED.categorie,
    gravite          = EXCLUDED.gravite,
    est_bloquant     = EXCLUDED.est_bloquant;

-- Vérification
SELECT * FROM dwh.dim_type_anomalie ORDER BY id_type_anomalie;