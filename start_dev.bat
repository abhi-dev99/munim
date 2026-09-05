@echo off
setlocal
echo ====================================================
echo  Munim.ai — Dev Server Starter
echo ====================================================

echo.
echo [1/5] Finding free ports (starting from 8004 backend / 3000 frontend)...
call :find_free_port 8004
set BACKEND_PORT=%FREEPORT%
call :find_free_port 3000
set FRONTEND_PORT=%FREEPORT%
echo      Backend  -^> port %BACKEND_PORT%
echo      Frontend -^> port %FRONTEND_PORT%
if not "%BACKEND_PORT%"=="8004" echo      (8004 was busy, moved on rather than killing whatever's using it)
if not "%FRONTEND_PORT%"=="3000" echo      (3000 was busy, moved on rather than killing whatever's using it)

echo.
echo [2/5] Wiring frontend/backend together for the ports actually chosen...
set "ADMIN_KEY="
if exist backend\.env (
    for /f "usebackq tokens=1,* delims==" %%a in ("backend\.env") do (
        if /i "%%a"=="ADMIN_API_KEY" set "ADMIN_KEY=%%b"
    )
)

rem --- backend/.env: make sure ALLOWED_ORIGINS covers whichever frontend port we picked ---
rem findstr reads the file directly rather than re-executing each line through
rem the shell, so comment lines containing literal | or & (e.g. the Redis/
rem ngrok comments already in this file) can't be misparsed as pipes/operators.
set "CORS_ORIGINS=http://localhost:%FRONTEND_PORT%,http://localhost:3000,http://localhost:3002,https://moaning-thwarting-dinginess.ngrok-free.dev"
set "TMP_BACKEND_ENV=backend\.env.tmp"
if exist backend\.env (
    findstr /v /b /c:"ALLOWED_ORIGINS=" backend\.env > "%TMP_BACKEND_ENV%"
) else (
    type nul > "%TMP_BACKEND_ENV%"
)
echo ALLOWED_ORIGINS=%CORS_ORIGINS%>> "%TMP_BACKEND_ENV%"
move /y "%TMP_BACKEND_ENV%" backend\.env >nul

rem --- frontend/.env.local: point it at wherever the backend actually landed ---
set "ENV_LOCAL=frontend\.env.local"
set "TMP_FRONTEND_ENV=frontend\.env.local.tmp"
if exist "%ENV_LOCAL%" (
    findstr /v /b /c:"NEXT_PUBLIC_API_URL=" /c:"NEXT_PUBLIC_ADMIN_API_KEY=" "%ENV_LOCAL%" > "%TMP_FRONTEND_ENV%"
) else (
    type nul > "%TMP_FRONTEND_ENV%"
)
echo NEXT_PUBLIC_API_URL=http://localhost:%BACKEND_PORT%>> "%TMP_FRONTEND_ENV%"
if defined ADMIN_KEY echo NEXT_PUBLIC_ADMIN_API_KEY=%ADMIN_KEY%>> "%TMP_FRONTEND_ENV%"
move /y "%TMP_FRONTEND_ENV%" "%ENV_LOCAL%" >nul

if not defined ADMIN_KEY (
    echo      NOTE: ADMIN_API_KEY isn't set in backend\.env, so the /dev
    echo      diagnostics page and Gemini key-pool controls will 403.
    echo      Add ADMIN_API_KEY=^<any long random string^> to backend\.env
    echo      to enable them.
)

echo.
echo [3/5] Starting Backend (FastAPI) on port %BACKEND_PORT%...
cd backend
start "Munim.ai Backend" cmd /k "title Munim.ai Backend && C:\Users\HP\AppData\Local\Programs\Python\Python312\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload"
cd ..

echo.
echo [4/5] Starting Frontend (Next.js) on port %FRONTEND_PORT%...
cd frontend
start "Munim.ai Frontend" cmd /k "title Munim.ai Frontend && npm.cmd run dev -- --port %FRONTEND_PORT%"
cd ..

echo.
echo [5/5] Starting Ngrok tunnel -^> port %BACKEND_PORT%...
start "Munim.ai Tunnel" cmd /k "title Munim.ai Tunnel && .\ngrok.exe http --domain=moaning-thwarting-dinginess.ngrok-free.dev %BACKEND_PORT%"

echo.
echo Waiting for tunnel to initialise...
timeout /t 4 /nobreak >nul

echo.
echo ====================================================
echo  All set, son!
echo  Frontend : http://localhost:%FRONTEND_PORT%
echo  Backend  : http://localhost:%BACKEND_PORT%
echo  Tunnel   : https://moaning-thwarting-dinginess.ngrok-free.dev
echo ====================================================
echo.
echo  Copy the Webhook URL above into Meta Developer Console
echo  if you want WhatsApp messages to reach this machine.
echo ====================================================
pause
endlocal
goto :eof

:find_free_port
setlocal
set "PORT=%~1"
:find_free_port_loop
netstat -aon | findstr ":%PORT% " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    set /a PORT+=1
    goto find_free_port_loop
)
endlocal & set "FREEPORT=%PORT%"
goto :eof
