@echo off
echo ============================================================
echo   Demarrage Airflow (Docker)
echo ============================================================
echo.

docker-compose up -d

echo.
echo Airflow demarre !
echo Interface : http://localhost:8080
echo Login     : admin / admin123
echo.
echo Attendez 30-60 secondes que tout demarre complement.
echo.

pause