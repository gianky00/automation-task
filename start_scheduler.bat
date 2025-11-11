@echo off
REM Crea la cartella dei log se non esiste
if not exist "logs" mkdir "logs"

REM Avvia il servizio di scheduling in modo silenzioso, reindirizzando l'output su un file di log.
REM 'start "Scheduler Service" /b' avvia il processo in background senza una nuova finestra.
REM 'pythonw.exe' esegue lo script senza una finestra di console.
REM '1>>logs\scheduler_startup.log' reindirizza l'output standard (stdout).
REM '2>>&1' reindirizza l'output di errore (stderr) allo stesso handle di stdout.
REM Questo cattura tutti gli output, inclusi gli errori di avvio, nel file di log
REM pur mantenendo il processo completamente invisibile all'utente.

start "Silent Scheduler Service" /b pythonw.exe scheduler_service.py 1>>logs\scheduler_startup.log 2>>&1
