-- ═══════════════════════════════════════════════════════════════
-- REFRESH DES VUES MATÉRIALISÉES
-- À exécuter périodiquement (via Airflow toutes les heures)
-- ═══════════════════════════════════════════════════════════════

-- Refresh CONCURRENTLY = non-bloquant (les utilisateurs PBI peuvent 
-- continuer à requêter pendant le refresh)

REFRESH MATERIALIZED VIEW CONCURRENTLY dwh.vw_pbi_carte_points_enrichie;

-- Vérifier la dernière date de refresh
SELECT 
    schemaname,
    matviewname,
    matviewowner,
    hasindexes,
    ispopulated
FROM pg_matviews
WHERE schemaname = 'dwh';