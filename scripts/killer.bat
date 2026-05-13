@REM @echo off
@REM echo Killing all processes using network ports...

@REM for /f "tokens=5" %%a in ('netstat -ano ^| findstr LISTENING') do (
@REM     echo Killing PID %%a
@REM     taskkill /F /PID %%a >nul 2>&1
@REM )

@REM echo Done.
@REM pause
@echo off
echo Killing processes using port 8000...

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo Killing PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo Done.
pause