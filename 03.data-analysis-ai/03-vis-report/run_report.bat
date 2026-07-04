@echo off
REM Run generate_report.py via conda environment
REM Used by Windows Task Scheduler

cd /d "%~dp0"

REM Activate conda environment (change "dbhitek" to your env name if different)
call "C:\Users\metam\miniconda3\condabin\conda.bat" activate dbhitek

if errorlevel 1 (
    echo Conda activation failed at %date% %time% >> scheduler_error.log
    exit /b 1
)

REM Run the report generation script
python generate_report.py

REM Deactivate
call conda deactivate