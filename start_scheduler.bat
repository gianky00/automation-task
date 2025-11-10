@echo off
REM Avvia il servizio di scheduling in una nuova finestra di console.
REM Questo permette di monitorare i log del servizio in tempo reale
REM senza bloccare la finestra del prompt principale.
start "Scheduler Service" python.exe scheduler_service.py
