@echo off
REM Avvia l'interfaccia grafica del configuratore di flussi.
REM L'uso di "pythonw.exe" permette di avviare l'applicazione
REM senza che la finestra del prompt dei comandi rimanga aperta.

REM %~dp0 si espande nel percorso della directory in cui si trova il file batch,
REM garantendo che lo script python venga trovato indipendentemente dalla directory di lavoro corrente.
start "Workflow Configurator GUI" pythonw.exe "%~dp0gui_configurator.py"
