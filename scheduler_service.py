import json
import logging
import os
import subprocess
import threading
import time
from datetime import datetime

CONFIG_FILE = os.path.join("config", "workflows.json")
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "scheduler.log")

# --- Configurazione del Logging ---
def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler() # Mostra i log anche in console
        ]
    )

# --- Funzione di Esecuzione del Flusso ---
def execute_flow(flow_name, tasks):
    """
    Esegue una lista di task in sequenza in un thread separato.
    """
    logging.info(f"TRIGGER: Avvio flusso '{flow_name}'.")

    for i, task_path in enumerate(tasks):
        logging.info(f"[{flow_name}] Esecuzione task {i+1}/{len(tasks)}: '{task_path}'...")

        if not os.path.exists(task_path):
            logging.error(f"[{flow_name}] ERRORE: Il file del task '{task_path}' non è stato trovato. Interruzione del flusso.")
            break # Interrompe il for loop, terminando il flusso

        try:
            start_time = time.monotonic()
            # subprocess.run attende la fine del processo, garantendo la sequenzialità
            result = subprocess.run(
                ["python", task_path],
                capture_output=True,
                text=True,
                check=False # Non solleva eccezioni per returncode != 0
            )
            end_time = time.monotonic()
            duration = end_time - start_time

            # Logga l'output standard del task
            if result.stdout:
                logging.info(f"[{flow_name}] Output di '{task_path}':\n{result.stdout.strip()}")

            if result.returncode == 0:
                logging.info(f"[{flow_name}] Task '{task_path}' completato con successo in {duration:.2f} secondi.")
            else:
                logging.error(f"[{flow_name}] ERRORE: Task '{task_path}' terminato con codice {result.returncode} dopo {duration:.2f} secondi.")
                # Logga l'output di errore
                if result.stderr:
                    logging.error(f"[{flow_name}] Errore di '{task_path}':\n{result.stderr.strip()}")
                logging.warning(f"[{flow_name}] Flusso interrotto a causa di un errore nel task.")
                break # Interrompe il for loop

        except Exception as e:
            logging.critical(f"[{flow_name}] Si è verificato un errore critico durante l'esecuzione di '{task_path}': {e}")
            logging.warning(f"[{flow_name}] Flusso interrotto a causa di un'eccezione.")
            break

    logging.info(f"Flusso '{flow_name}' terminato.")


# --- Servizio Scheduler Principale ---
def scheduler_service():
    logging.info("Servizio Scheduler avviato. In attesa di flussi da eseguire...")

    last_execution_dates = {} # Dizionario per tracciare l'ultima esecuzione: {flow_name: "YYYY-MM-DD"}

    while True:
        try:
            # 1. Carica la configurazione
            try:
                with open(CONFIG_FILE, 'r') as f:
                    workflows = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                logging.warning("File di configurazione non trovato o corrotto. Riprovo tra 60 secondi.")
                time.sleep(60)
                continue

            # 2. Ottieni data e ora correnti
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            current_day_of_week = now.weekday() # Lunedì=0, Domenica=6
            current_date_str = now.strftime("%Y-%m-%d")

            logging.info(f"Controllo orario: {current_time}, Giorno: {current_day_of_week}")

            # 3. Itera su tutti i flussi configurati
            for flow_name, config in workflows.items():

                # 4. Verifica le condizioni di trigger
                is_time_to_run = (config.get("schedule_time") == current_time)
                is_day_to_run = (current_day_of_week in config.get("schedule_days", []))

                # Controlla se è già stato eseguito oggi
                has_run_today = (last_execution_dates.get(flow_name) == current_date_str)

                if is_time_to_run and is_day_to_run and not has_run_today:
                    tasks = config.get("tasks", [])
                    if not tasks:
                        logging.warning(f"Il flusso '{flow_name}' è pianificato ma non ha task. Salto.")
                        continue

                    # Avvia l'esecuzione in un thread per non bloccare il loop
                    execution_thread = threading.Thread(
                        target=execute_flow,
                        args=(flow_name, tasks)
                    )
                    execution_thread.start()

                    # Aggiorna lo stato per evitare riesecuzioni
                    last_execution_dates[flow_name] = current_date_str

            # 5. Attendi prima del prossimo controllo
            time.sleep(60)

        except KeyboardInterrupt:
            logging.info("Rilevato KeyboardInterrupt. Arresto del servizio scheduler...")
            break
        except Exception as e:
            logging.critical(f"Errore non gestito nel loop principale dello scheduler: {e}")
            time.sleep(60) # Attendi prima di riprovare

if __name__ == "__main__":
    setup_logging()
    scheduler_service()
