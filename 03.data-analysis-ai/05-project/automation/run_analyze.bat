@echo off
REM Run analyze_one_day.py via conda environment
REM Used by Windows Task Scheduler

cd /d "%~dp0"

REM Activate conda environment (change "dbhitek" to your env name if different)
call "C:\Users\metam\miniconda3\condabin\conda.bat" activate dbhitek

if errorlevel 1 (
    echo Conda activation failed at %date% %time% >> scheduler_error.log
    exit /b 1
)

REM Run the analysis script
python analyze_one_day.py

REM Deactivate
call conda deactivate