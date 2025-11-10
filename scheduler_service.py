import json
import logging
import os
import threading
import time
from datetime import datetime
from core_logic import setup_logging, execute_flow

CONFIG_FILE = os.path.join("config", "workflows.json")

def scheduler_service():
    """
    Servizio principale che controlla e avvia i flussi di lavoro pianificati.
    """
    logging.info("Servizio Scheduler avviato. In attesa di flussi da eseguire...")

    last_execution_dates = {}

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

            logging.info(f"Controllo orario: {current_time}, Giorno: {current_day_of_week}")

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
                        target=execute_flow,
                        args=(flow_name, tasks)
                    )
                    execution_thread.start()

                    last_execution_dates[flow_name] = current_date_str

            time.sleep(60)

        except KeyboardInterrupt:
            logging.info("Rilevato KeyboardInterrupt. Arresto del servizio scheduler...")
            break
        except Exception as e:
            logging.critical(f"Errore non gestito nel loop principale dello scheduler: {e}")
            time.sleep(60)

if __name__ == "__main__":
    setup_logging()
    scheduler_service()
