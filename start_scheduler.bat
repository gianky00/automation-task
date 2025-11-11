@echo off
REM Avvia il servizio di scheduling in modo completamente silenzioso in background.
REM 'start /b' avvia il processo senza creare una nuova finestra.
REM 'pythonw.exe' è l'interprete Python che non apre una finestra di console.
REM Insieme, garantiscono che il servizio giri in modo invisibile.

start "Silent Scheduler Service" /b pythonw.exe scheduler_service.py
