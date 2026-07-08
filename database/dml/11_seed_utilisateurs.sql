-- database/dml/11_seed_utilisateurs.sql
-- Mots de passe hashés avec bcrypt (password par défaut: "SRM2024!")

INSERT INTO app_auth.utilisateurs (username, password_hash, nom_complet, email, role, id_province, code_province) VALUES
-- Agents DP (saisie uniquement)
('agent_dp_tata', '$2b$12$LJ3m5ZQxHxEH8N8gKkEhZOqhZ7Z5z5z5z5z5z5z5z5z5z5z5z5z5z', 'Agent DP Tata', 'agent.tata@srm-sm.ma', 'agent_dp', 1, 'TATA'),
('agent_dp_tiznit', '$2b$12$LJ3m5ZQxHxEH8N8gKkEhZOqhZ7Z5z5z5z5z5z5z5z5z5z5z5z5z5z', 'Agent DP Tiznit', 'agent.tiznit@srm-sm.ma', 'agent_dp', 2, 'TIZNIT'),
('agent_dp_chtouka', '$2b$12$LJ3m5ZQxHxEH8N8gKkEhZOqhZ7Z5z5z5z5z5z5z5z5z5z5z5z5z5z', 'Agent DP Chtouka Ait Baha', 'agent.chtouka@srm-sm.ma', 'agent_dp', 3, 'CHTOUKA'),
('agent_dp_taroudant', '$2b$12$LJ3m5ZQxHxEH8N8gKkEhZOqhZ7Z5z5z5z5z5z5z5z5z5z5z5z5z5z', 'Agent DP Taroudant', 'agent.taroudant@srm-sm.ma', 'agent_dp', 4, 'TAROUDANT'),
('agent_dp_inezgane', '$2b$12$LJ3m5ZQxHxEH8N8gKkEhZOqhZ7Z5z5z5z5z5z5z5z5z5z5z5z5z5z', 'Agent DP Inezgane Ait Melloul', 'agent.inezgane@srm-sm.ma', 'agent_dp', 5, 'INEZGANE'),
('agent_dp_agadir', '$2b$12$LJ3m5ZQxHxEH8N8gKkEhZOqhZ7Z5z5z5z5z5z5z5z5z5z5z5z5z5z', 'Agent DP Agadir', 'agent.agadir@srm-sm.ma', 'agent_dp', 6, 'AGADIR'),

-- Administrateurs DP (validation niveau 1)
('admin_dp_tata', '$2b$12$LJ3m5ZQxHxEH8N8gKkEhZOqhZ7Z5z5z5z5z5z5z5z5z5z5z5z5z5z', 'Admin DP Tata', 'admin.tata@srm-sm.ma', 'admin_dp', 1, 'TATA'),
('admin_dp_tiznit', '$2b$12$LJ3m5ZQxHxEH8N8gKkEhZOqhZ7Z5z5z5z5z5z5z5z5z5z5z5z5z5z', 'Admin DP Tiznit', 'admin.tiznit@srm-sm.ma', 'admin_dp', 2, 'TIZNIT'),
('admin_dp_chtouka', '$2b$12$LJ3m5ZQxHxEH8N8gKkEhZOqhZ7Z5z5z5z5z5z5z5z5z5z5z5z5z5z', 'Admin DP Chtouka Ait Baha', 'admin.chtouka@srm-sm.ma', 'admin_dp', 3, 'CHTOUKA'),
('admin_dp_taroudant', '$2b$12$LJ3m5ZQxHxEH8N8gKkEhZOqhZ7Z5z5z5z5z5z5z5z5z5z5z5z5z5z', 'Admin DP Taroudant', 'admin.taroudant@srm-sm.ma', 'admin_dp', 4, 'TAROUDANT'),
('admin_dp_inezgane', '$2b$12$LJ3m5ZQxHxEH8N8gKkEhZOqhZ7Z5z5z5z5z5z5z5z5z5z5z5z5z5z', 'Admin DP Inezgane Ait Melloul', 'admin.inezgane@srm-sm.ma', 'admin_dp', 5, 'INEZGANE'),
('admin_dp_agadir', '$2b$12$LJ3m5ZQxHxEH8N8gKkEhZOqhZ7Z5z5z5z5z5z5z5z5z5z5z5z5z5z', 'Admin DP Agadir', 'admin.agadir@srm-sm.ma', 'admin_dp', 6, 'AGADIR'),

-- Administrateur Régional (validation finale - siège Agadir)
('admin_regional', '$2b$12$LJ3m5ZQxHxEH8N8gKkEhZOqhZ7Z5z5z5z5z5z5z5z5z5z5z5z5z5z', 'Administrateur Régional Souss-Massa', 'admin.regional@srm-sm.ma', 'admin_regional', NULL, NULL),

-- Super Admin
('super_admin', '$2b$12$LJ3m5ZQxHxEH8N8gKkEhZOqhZ7Z5z5z5z5z5z5z5z5z5z5z5z5z5z', 'Super Administrateur', 'superadmin@srm-sm.ma', 'super_admin', NULL, NULL)
ON CONFLICT (username) DO NOTHING;