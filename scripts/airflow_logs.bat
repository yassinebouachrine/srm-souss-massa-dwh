@echo off
echo ============================================================
echo   Logs Airflow (Ctrl+C pour quitter)
echo ============================================================
echo.

docker-compose logs -f airflow-webserver airflow-scheduler

pause