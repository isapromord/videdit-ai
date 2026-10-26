@echo off
title VIDEDIT AI Studio - Editor de Video por Palabras
cd /d "C:\Users\howar\Desktop\APPS\MIS APPS\VIDEDIT"
echo ========================================================
echo   VIDEDIT AI - Standalone AI Video VFX & Prompt Studio
echo   Acceso Local: http://localhost:8686
echo   (El video original se mantiene siempre 100% intacto)
echo ========================================================
python -m uvicorn server:app --host 0.0.0.0 --port 8686
pause
