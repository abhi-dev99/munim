@echo off
echo ====================================================
echo Munim.ai - Smart Dev Server Starter
echo ====================================================

echo.
echo [0/3] Pulling latest code from GitHub...
git pull origin main

echo.
echo [1/3] Cleaning up old server instances...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| find "LISTENING"') do (
    echo Killing process %%a on port 8000 Backend
    taskkill /f /pid %%a 2>nul
)

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| find "LISTENING"') do (
    echo Killing process %%a on port 3000 Frontend
    taskkill /f /pid %%a 2>nul
)

timeout /t 2 /nobreak >nul

echo.
echo [2/3] Starting Backend FastAPI on port 8000...
cd backend
start "Munim.ai Backend" cmd /k "title Munim.ai Backend && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
cd ..

echo.
echo [3/3] Starting Frontend Next.js on port 3000...
cd frontend
start "Munim.ai Frontend" cmd /k "title Munim.ai Frontend && npm run dev"
cd ..

echo.
echo ====================================================
echo All set, son! 
echo Frontend is booting at: http://localhost:3000
echo Backend is booting at:  http://localhost:8000
echo ====================================================
pause
