# Automation Task - Pianificatore di Flussi Sequenziali

Questo progetto è un'applicazione Python per creare, pianificare ed eseguire flussi di lavoro composti da più task. È progettato per garantire che i task all'interno di un flusso vengano eseguiti in modo **strettamente sequenziale**, dove un task inizia solo dopo che il precedente è terminato.

## Architettura

Il sistema è diviso in due componenti principali:

1.  **Configuratore GUI (`gui_configurator.py`)**
    - Un'interfaccia grafica creata con Tkinter che permette di:
        - Creare e gestire più flussi di lavoro.
        - Aggiungere, rimuovere e riordinare task (script Python) per ogni flusso.
        - Impostare una pianificazione precisa (ora e giorni della settimana) per l'esecuzione automatica.
    - Tutte le configurazioni vengono salvate in un file `config/workflows.json`.

2.  **Servizio Scheduler (`scheduler_service.py`)**
    - Uno script autonomo progettato per essere eseguito in background 24/7.
    - Legge periodicamente il file `config/workflows.json` per caricare le pianificazioni.
    - Avvia i flussi di lavoro all'orario e nei giorni specificati.
    - Gestisce l'esecuzione sequenziale dei task e registra tutte le operazioni nel file `logs/scheduler.log`.

## Come Avviare l'Applicazione (Windows)

Per semplificare l'avvio, sono stati forniti due script batch.

### 1. Avviare il Configuratore GUI

Per creare o modificare i flussi di lavoro, esegui:

```batch
start_gui.bat
```

Questo comando aprirà l'interfaccia grafica. Grazie all'uso di `pythonw.exe`, la finestra del prompt dei comandi non rimarrà visibile.

### 2. Avviare il Servizio di Scheduling

Affinché i flussi vengano eseguiti automaticamente, il servizio di scheduling deve essere in esecuzione. Per avviarlo, esegui:

```batch
start_scheduler.bat
```

Questo comando aprirà una **nuova finestra di console** dove potrai vedere i log del servizio in tempo reale. Puoi minimizzare questa finestra e lasciarla in esecuzione in background.

**Importante:** Il servizio scheduler deve rimanere in esecuzione per garantire che i tuoi flussi di lavoro vengano attivati come pianificato.
