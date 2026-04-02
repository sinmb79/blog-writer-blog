@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ============================================
echo   Blog Writer Blog - n8n Setup
echo   Collect, write, review, and publish.
echo ============================================
echo.

set "ROOT_DIR=%~dp0"
set "WORKFLOW_DIR=%ROOT_DIR%n8n-workflows"
set "LOG_DIR=%ROOT_DIR%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

echo [1/4] 필수 도구 확인 중...
where node >nul 2>&1 || (echo   ❌ Node.js가 필요합니다. https://nodejs.org && exit /b 1)
echo   ✅ node 확인됨
where npm >nul 2>&1 || (echo   ❌ npm이 필요합니다. && exit /b 1)
echo   ✅ npm 확인됨
where python >nul 2>&1 || (echo   ❌ Python이 필요합니다. https://www.python.org/downloads/ && exit /b 1)
echo   ✅ python 확인됨
where curl >nul 2>&1 || (echo   ❌ curl이 필요합니다. Windows 10+ 기본 포함이 아니면 설치해 주세요. && exit /b 1)
echo   ✅ curl 확인됨
echo.

echo [2/4] n8n 설치 중...
where n8n >nul 2>&1 && (
  for /f "delims=" %%i in ('n8n --version') do set "N8N_VERSION=%%i"
  echo   ✅ n8n 이미 설치됨 (!N8N_VERSION!)
) || (
  echo   📦 n8n 설치 중...
  npm install -g n8n || exit /b 1
  echo   ✅ n8n 설치 완료
)
echo.

echo [3/4] n8n 시작 중...
curl -s --max-time 2 http://localhost:5678/healthz >nul 2>&1
if %errorlevel%==0 (
  echo   ✅ n8n 이미 실행 중입니다.
) else (
  echo   🚀 n8n 백그라운드 시작...
  start "" /B cmd /v:on /c "cd /d ""%ROOT_DIR%"" && n8n start > ""%LOG_DIR%\n8n.log"" 2>&1"
  echo   ⏳ n8n 시작 대기 중...
  set "READY="
  for /L %%i in (1,1,30) do (
    curl -s --max-time 2 http://localhost:5678/healthz >nul 2>&1
    if !errorlevel!==0 (
      set "READY=1"
      goto :n8n_ready
    )
    timeout /t 1 /nobreak >nul
  )
  :n8n_ready
  if not defined READY (
    echo   ❌ n8n 시작 실패. 로그 확인: %LOG_DIR%\n8n.log
    exit /b 1
  )
  echo   ✅ n8n 시작 완료
)
echo.

echo [4/4] 워크플로우 임포트 중...
call :import "%WORKFLOW_DIR%\blog-daily-pipeline.json" "Daily Pipeline"
call :import "%WORKFLOW_DIR%\blog-write-queue.json" "Write Queue"
call :import "%WORKFLOW_DIR%\blog-publish-queue.json" "Publish Queue"
call :import "%WORKFLOW_DIR%\blog-weekly-report.json" "Weekly Report"
call :import "%WORKFLOW_DIR%\blog-monthly-reminder.json" "Monthly Reminder"
echo.

echo ============================================
echo   Blog Writer Blog 준비 완료
echo.
echo   n8n: http://localhost:5678
echo   로그: %LOG_DIR%\n8n.log
echo.
echo   브라우저에서 n8n을 열면 5개 워크플로우가 보여야 합니다.
echo ============================================

start "" http://localhost:5678
exit /b 0

:import
if exist "%~1" (
  n8n import:workflow --input="%~1" >nul 2>&1 && (
    echo   ✅ %~2
  ) || (
    echo   ⚠️  %~2 임포트 실패
  )
) else (
  echo   ⚠️  %~2 파일 없음: %~1
)
exit /b 0
