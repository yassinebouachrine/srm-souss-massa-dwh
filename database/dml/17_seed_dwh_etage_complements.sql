-- ═══════════════════════════════════════════════════════════════
-- SEED — Compléments DIM_ETAGE
-- Étages découverts dans les fichiers référentiels Étoile C
-- ═══════════════════════════════════════════════════════════════

-- Étage IMOUNSSISS (référencé dans la matrice loc_sec)
INSERT INTO dwh.dim_etage 
    (id_etage, code_etage, nom_etage, type_etage, lineaire_km, nom_region, nom_province)
VALUES
    (17, 'ETAGE_IMOUNSSISS', 'IMOUNSSISS', 'Réservoir', NULL, 'Souss-Massa', 'Agadir')
ON CONFLICT (id_etage) DO UPDATE
SET code_etage = EXCLUDED.code_etage,
    nom_etage  = EXCLUDED.nom_etage;


-- Étage ANZA agrégé (ANZA 70 + ANZA 101)
INSERT INTO dwh.dim_etage 
    (id_etage, code_etage, nom_etage, type_etage, nom_region, nom_province)
VALUES
    (94, 'ETAGE_ANZA_AGG', 'ANZA 70+ ANZA 101', 'Agrégation', 'Souss-Massa', 'Agadir')
ON CONFLICT (id_etage) DO UPDATE
SET code_etage = EXCLUDED.code_etage,
    nom_etage  = EXCLUDED.nom_etage;


-- Vérification
SELECT id_etage, code_etage, nom_etage, type_etage, lineaire_km
FROM dwh.dim_etage
ORDER BY id_etage;