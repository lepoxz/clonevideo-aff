@echo off
echo Starting CloneVideo-Aff Backend (Port 8000)...
start "CloneVideo-Aff Backend" cmd /k "cd /d d:\clonevideo\backend && C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

echo Starting CloneVideo-Aff Frontend (Port 5173)...
start "CloneVideo-Aff Frontend" cmd /k "cd /d d:\clonevideo\frontend && npm run dev -- --port 5173"

echo.
echo Dashboard: http://localhost:5173
echo API Docs:  http://127.0.0.1:8000/docs
echo Bio Page:  http://127.0.0.1:8000/bio
pause
