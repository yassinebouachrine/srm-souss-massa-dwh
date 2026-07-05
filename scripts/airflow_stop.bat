@echo off
echo ============================================================
echo   Arret Airflow (Docker)
echo ============================================================
echo.

docker-compose down

echo.
echo Airflow arrete !
echo Les donnees sont preservees dans le volume Docker.
echo.

pause