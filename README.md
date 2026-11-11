# Automation Task — Sequential Workflow Scheduler & Orchestrator

![Python](https://img.shields.io/badge/Python-3.10+%20(Zero%20External%20Deps)-3776AB?style=flat-square&logo=python&logoColor=white)
![Concurrency](https://img.shields.io/badge/Concurrency-Thread--Safe%20Atomic%20I%2FO-0284C7?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows%20Desktop%20%26%20Service-0F172A?style=flat-square)

Sistema leggero di orchestrazione e scheduling sviluppato interamente con la **Standard Library di Python** per configurare, pianificare ed eseguire **flussi di lavoro strettamente sequenziali** (pipeline di script Python, batch o task importati dall'Utilità di Pianificazione di Windows).

---

## Caratteristiche Tecniche

- **Esecuzione Sequenziale Garantita (`core_logic.py`):** Ogni flusso di lavoro esegue i propri task in cascata rigorosa: lo step successivo viene avviato solo al completamento del precedente, evitando race condition su file Excel o database condivisi.
- **Persistenza Atomica Thread-Safe (`safe_save_json`):** Tutte le scritture dei file di stato e delle statistiche utilizzano il pattern transazionale *Write-to-Temp & Atomic Rename* protetto da lock (`threading.Lock`) per prevenire qualsiasi corruzione dei file JSON durante accessi concorrenti tra GUI e servizio di background.
- **Importazione Nativa Task Windows (`_parse_task_path_from_xml`):** Parsing diretto dei file `.xml` esportati dal *Windows Task Scheduler* per convertire rapidamente attività legacy in pipeline gestite.
- **Architettura Disaccoppiata (GUI + Background Service):**
  - `gui_configurator.py`: Interfaccia desktop con coda di logging in tempo reale (`QueueHandler`) per creare i flussi, riordinare i task, impostare giorni/orari di esecuzione e monitorare le statistiche.
  - `scheduler_service.py`: Demone leggero progettato per restare attivo in background, verificare le pianificazioni in `config/workflows.json` e tracciare i flussi attivi con PID in `scheduler_status.json`.

---

## Struttura del Progetto

```text
automation-task/
├── config/
│   └── workflows.json          # Definizione dei flussi, sequenza task e pianificazione oraria
├── scripts/
│   └── install_autostart.py    # Configurazione avvio automatico del servizio su Windows
├── tests/
│   ├── test_core_logic.py      # Test unitari su esecuzione flussi e I/O atomico
│   ├── test_scheduler_service.py
│   └── verify_concurrency.py   # Stress test di concorrenza e thread-safety
├── core_logic.py               # Motore di esecuzione, gestione lock e salvataggio atomico
├── gui_configurator.py         # Interfaccia grafica di configurazione e monitoraggio
├── scheduler_service.py        # Servizio di scheduling in background
└── start_gui.bat               # Avvio rapido dell'interfaccia senza finestra console
```

---

## Avvio e Test

Non è richiesta alcuna dipendenza esterna (`pip install` non necessario per il runtime).

```powershell
# Avvio del configuratore grafico
start_gui.bat
# oppure:
python gui_configurator.py

# Avvio del servizio di scheduling in background
python scheduler_service.py

# Esecuzione dei test unitari e di concorrenza
python -m unittest discover -s tests
```

---

## Autore
Progettato e sviluppato da **Giancarlo Allegretti** — *Industrial Automation, Instrumentation & AI Software Engineering*.
