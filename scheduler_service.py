import json
import logging
import os
import threading
import time
from datetime import datetime
from core_logic import setup_logging, execute_flow

CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "workflows.json")
STATUS_FILE = os.path.join(CONFIG_DIR, "scheduler_status.json")

# Stato condiviso per i flussi attivi
_active_flows = set()
_status_lock = threading.Lock()

def _update_status_file():
    """Scrive lo stato corrente (PID, flussi attivi) nel file di stato."""
    with _status_lock:
        status = {
            'pid': os.getpid(),
            'running_flows': list(_active_flows),
            'timestamp': datetime.now().isoformat()
        }
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=4)

def _clear_status_file():
    """Rimuove il file di stato, se esiste."""
    with _status_lock:
        if os.path.exists(STATUS_FILE):
            os.remove(STATUS_FILE)

def flow_execution_wrapper(flow_name, tasks):
    """
    Wrapper per l'esecuzione di un flusso che gestisce l'aggiornamento
    dello stato (aggiunta/rimozione dalla lista dei flussi attivi).
    """
    with _status_lock:
        _active_flows.add(flow_name)
    _update_status_file()

    try:
        # Esegui il flusso vero e proprio
        execute_flow(flow_name, tasks)
    finally:
        # Assicura la rimozione dallo stato anche in caso di errore
        with _status_lock:
            _active_flows.remove(flow_name)
        _update_status_file()

def scheduler_service():
    """
    Servizio principale che controlla e avvia i flussi di lavoro pianificati.
    """
    logging.info("Servizio Scheduler avviato. In attesa di flussi da eseguire...")

    last_execution_dates = {}

    try:
        _update_status_file() # Scrivi lo stato iniziale

        while True:
            try:
                try:
                    with open(CONFIG_FILE, 'r') as f:
                        workflows = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    logging.warning("File di configurazione non trovato o corrotto. Riprovo tra 60 secondi.")
                    time.sleep(60)
                    continue

                now = datetime.now()
                current_time = now.strftime("%H:%M")
                current_day_of_week = now.weekday()
                current_date_str = now.strftime("%Y-%m-%d")

                logging.info(f"Controllo orario: {current_time}, Giorno: {current_day_of_week}, Flussi attivi: {len(_active_flows)}")

                for flow_name, config in workflows.items():
                    is_time_to_run = (config.get("schedule_time") == current_time)
                    is_day_to_run = (current_day_of_week in config.get("schedule_days", []))
                    has_run_today = (last_execution_dates.get(flow_name) == current_date_str)

                    if is_time_to_run and is_day_to_run and not has_run_today:
                        tasks = config.get("tasks", [])
                        if not tasks:
                            logging.warning(f"Il flusso '{flow_name}' è pianificato ma non ha task. Salto.")
                            continue

                        execution_thread = threading.Thread(
                            target=flow_execution_wrapper, # Usa il wrapper
                            args=(flow_name, tasks)
                        )
                        execution_thread.start()

                        last_execution_dates[flow_name] = current_date_str

                # Aggiorna il timestamp del file di stato anche se non ci sono nuove esecuzioni
                _update_status_file()
                time.sleep(60)

            except KeyboardInterrupt:
                logging.info("Rilevato KeyboardInterrupt. Arresto del servizio scheduler...")
                break
            except Exception as e:
                logging.critical(f"Errore non gestito nel loop principale dello scheduler: {e}")
                time.sleep(60)
    finally:
        logging.info("Pulizia e arresto del servizio...")
        _clear_status_file() # Assicura che il file di stato sia rimosso all'uscita

if __name__ == "__main__":
    setup_logging()
    scheduler_service()
