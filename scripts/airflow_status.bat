@echo off
echo ============================================================
echo   Etat des conteneurs Airflow
echo ============================================================
echo.

docker ps --filter "name=srm_"

echo.
pause