@echo off
setlocal
echo ====================================================
echo  Munim.ai — Dev Server Starter
echo ====================================================

echo.
echo [0/4] Pulling latest code from GitHub...
git pull origin main

echo.
echo [1/4] Killing anything on ports 8000 / 3000 / 4040...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000 " ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":4040 " ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)
timeout /t 2 /nobreak >nul

echo.
echo [2/4] Starting Backend (FastAPI) on port 8000...
cd backend
start "Munim.ai Backend" cmd /k "title Munim.ai Backend && C:\Users\HP\AppData\Local\Programs\Python\Python312\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
cd ..

echo.
echo [3/4] Starting Frontend (Next.js) on port 3000...
cd frontend
start "Munim.ai Frontend" cmd /k "title Munim.ai Frontend && set PATH=C:\Users\HP\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin;%PATH% && node node_modules\next\dist\bin\next dev"
cd ..

echo.
echo [4/4] Starting ngrok tunnel on port 8000...
start "Munim.ai ngrok" cmd /k "title Munim.ai ngrok && ngrok http 8000"

echo.
echo Waiting for ngrok to initialise...
timeout /t 4 /nobreak >nul

echo.
echo Fetching ngrok public URL...
for /f "delims=" %%u in ('python -c "import urllib.request,json; d=json.loads(urllib.request.urlopen(\"http://127.0.0.1:4040/api/tunnels\").read()); print(d[\"tunnels\"][0][\"public_url\"])" 2^>nul') do set NGROK_URL=%%u

echo.
echo ====================================================
echo  All set, son!
echo  Frontend : http://localhost:3000
echo  Backend  : http://localhost:8000
if defined NGROK_URL (
echo  ngrok    : %NGROK_URL%
echo  Webhook  : %NGROK_URL%/api/v1/webhook
) else (
echo  ngrok    : still booting — check the ngrok window
)
echo ====================================================
echo.
echo  Copy the Webhook URL above into Meta Developer Console
echo  if you want WhatsApp messages to reach this machine.
echo ====================================================
pause
endlocal
