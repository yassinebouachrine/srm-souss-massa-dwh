-- ═══════════════════════════════════════════════════════════════
-- SEED DWH — Centre sentinelle pour agrégation DP
-- 
-- Utilisé quand une ligne de fait concerne un DP entier
-- (onglet "Recap DP" dans les Excel) sans centre spécifique.
-- Pattern Kimball : "Unknown/Aggregate Member"
-- ═══════════════════════════════════════════════════════════════

-- Insérer le centre sentinelle avec id_centre = 0 (réservé)
-- Utilise INSERT direct pour forcer id_centre = 0 (pas de nextval)
INSERT INTO dwh.dim_centre (id_centre, code_centre, nom_centre, type_centre, code_dp, nom_dp)
VALUES (0, 'AGREG_DP', 'Agrégation DP (Recap)', 'Agrégation', 'ALL', 'Tous les DP')
ON CONFLICT (id_centre) DO UPDATE SET
    code_centre = EXCLUDED.code_centre,
    nom_centre  = EXCLUDED.nom_centre,
    type_centre = EXCLUDED.type_centre;

-- Vérification
SELECT id_centre, code_centre, nom_centre, type_centre 
FROM dwh.dim_centre 
WHERE id_centre = 0;