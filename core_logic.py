import logging
import os
import subprocess
import time

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "scheduler.log")

def setup_logging():
    """Configura il sistema di logging per scrivere su file e console."""
    os.makedirs(LOG_DIR, exist_ok=True)

    # Rimuovi eventuali handler esistenti per evitare log duplicati
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )

def execute_flow(flow_name, tasks):
    """
    Esegue una lista di task (dizionari con 'name' e 'path') in sequenza.
    """
    logging.info(f"TRIGGER: Avvio flusso '{flow_name}'.")

    for i, task in enumerate(tasks):
        task_name = task.get('name', 'Task Senza Nome')
        task_path = task.get('path', '')

        logging.info(f"[{flow_name}] Esecuzione task {i+1}/{len(tasks)} '{task_name}': '{task_path}'...")

        if not task_path or not os.path.exists(task_path):
            logging.error(f"[{flow_name}] ERRORE: Il file del task '{task_name}' ('{task_path}') non è stato trovato. Interruzione del flusso.")
            break

        try:
            command = []
            file_extension = os.path.splitext(task_path)[1].lower()

            if file_extension == '.py':
                command = ["python", task_path]
            elif file_extension == '.bat':
                command = ["cmd", "/c", task_path]
            elif file_extension == '.ps1':
                command = ["powershell", "-ExecutionPolicy", "Bypass", "-File", task_path]
            else:
                logging.error(f"[{flow_name}] ERRORE: Tipo di file non supportato '{file_extension}' per il task '{task_name}'. Salto.")
                continue

            start_time = time.monotonic()
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                encoding='utf-8',
                errors='replace'
            )
            end_time = time.monotonic()
            duration = end_time - start_time

            if result.stdout:
                logging.info(f"[{flow_name}] Output del task '{task_name}':\n{result.stdout.strip()}")

            if result.returncode == 0:
                logging.info(f"[{flow_name}] Task '{task_name}' completato con successo in {duration:.2f} secondi.")
                if i < len(tasks) - 1:
                    next_task_name = tasks[i+1].get('name', 'Task Senza Nome')
                    logging.info(f"[{flow_name}] Prossimo task: '{next_task_name}'")
            else:
                logging.error(f"[{flow_name}] ERRORE: Task '{task_name}' terminato con codice {result.returncode} dopo {duration:.2f} secondi.")
                if result.stderr:
                    logging.error(f"[{flow_name}] Errore standard del task '{task_name}':\n{result.stderr.strip()}")
                logging.warning(f"[{flow_name}] Flusso interrotto a causa di un errore nel task.")
                break

        except Exception as e:
            logging.critical(f"[{flow_name}] Errore critico durante l'esecuzione del task '{task_name}': {e}")
            logging.warning(f"[{flow_name}] Flusso interrotto a causa di un'eccezione.")
            break

    logging.info(f"Flusso '{flow_name}' terminato.")
