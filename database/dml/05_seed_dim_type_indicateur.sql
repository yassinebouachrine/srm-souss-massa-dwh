TRUNCATE TABLE gold.dim_type_indicateur_dp CASCADE;

INSERT INTO gold.dim_type_indicateur_dp 
    (code_indicateur, libelle_indicateur, unite, categorie, sous_categorie, 
     ligne_source_excel, est_calculable, formule_calcul, ordre_affichage)
VALUES
    ('REND', 'Rendement', '%', 'Performance', 'Ratio', 2, TRUE, 'Ventes / Achats', 1),
    ('ILP', 'Indice Lineaire de Pertes', 'm3/jr/km', 'Performance', 'Ratio', 3, TRUE, 'Pertes / (Lineaire × Nb_Jours)', 2),
    ('AGE_CPT', 'Age moyen compteurs Eau', 'An', 'Parc_Compteurs', 'Vetuste', 4, FALSE, NULL, 3),
    ('NB_CLI', 'Nombre clients', 'U', 'Commercial', 'Volume', 5, FALSE, NULL, 4),
    ('NB_FRAUD', 'Nombre de fraudes Eau', 'U', 'Fraudes', 'Volume', 6, FALSE, NULL, 5),
    ('VOL_FRAUD', 'Volume Fraudes', 'm3', 'Fraudes', 'Volume', 7, FALSE, NULL, 6),
    ('ACHAT', 'Achats', 'm3', 'Production', 'Volume', 8, FALSE, NULL, 7),
    ('VENTE', 'Ventes', 'm3', 'Commercial', 'Volume', 9, FALSE, NULL, 8),
    ('LIN_RES', 'Lineaire reseau', 'km', 'Infrastructure', 'Longueur', 10, FALSE, NULL, 9),
    ('RECH_FUIT', 'Recherche de fuites', 'km', 'Maintenance', 'Longueur', 11, FALSE, NULL, 10),
    ('FUIT_CDT', 'Fuites sur conduite', 'U', 'Maintenance', 'Comptage', 12, FALSE, NULL, 11),
    ('FUIT_BRT', 'Fuites sur Branchement', 'U', 'Maintenance', 'Comptage', 13, FALSE, NULL, 12),
    ('FUIT_CPT', 'Fuites compteurs/PS', 'U', 'Maintenance', 'Comptage', 14, FALSE, NULL, 13),
    ('RED_PRESS', 'Reducteurs de pression', 'U', 'Infrastructure', 'Comptage', 15, FALSE, NULL, 14),
    ('SEC_HYD', 'Secteurs hydrauliques', 'U', 'Infrastructure', 'Comptage', 16, FALSE, NULL, 15),
    ('RES_RENOV', 'Reseau renouvele', 'km', 'Renouvellement', 'Longueur', 17, FALSE, NULL, 16),
    ('BRT_RENOV', 'Branchements renouveles', 'U', 'Renouvellement', 'Comptage', 18, FALSE, NULL, 17),
    ('CPT_RENOV', 'Compteurs renouveles', 'U', 'Renouvellement', 'Comptage', 19, FALSE, NULL, 18),
    ('ETG_PRESS', 'Etages de pression', 'U', 'Infrastructure', 'Comptage', 20, FALSE, NULL, 19),
    ('AUTOPROD', 'Autoproduction', 'm3', 'Production', 'Volume', 21, FALSE, NULL, 20),
    ('CESSION', 'Cession', 'm3', 'Production', 'Volume', 22, FALSE, NULL, 21);

SELECT COUNT(*) AS nb_indicateurs FROM gold.dim_type_indicateur_dp;