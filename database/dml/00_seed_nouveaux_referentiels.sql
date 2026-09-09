-- ═══════════════════════════════════════════════════════════════
-- INSERTION DES NOUVELLES DONNÉES DE RÉFÉRENCE
-- ═══════════════════════════════════════════════════════════════

-- 1. Rôles
INSERT INTO app_auth.ref_role (id_role, code_role, libelle_role) VALUES
(1, 'agent_dp', 'Agent DP'),
(2, 'admin_dp', 'Administrateur DP'),
(3, 'admin_regional', 'Administrateur Régional'),
(4, 'super_admin', 'Super Administrateur')
ON CONFLICT (code_role) DO UPDATE 
SET libelle_role = EXCLUDED.libelle_role;

-- 2. Périodes (Génère automatiquement les mois de 2024 à 2030)
INSERT INTO app_staging.ref_periode (annee, mois)
SELECT y, m
FROM generate_series(2024, 2030) AS y,
     generate_series(1, 12) AS m
ON CONFLICT (annee, mois) DO NOTHING;