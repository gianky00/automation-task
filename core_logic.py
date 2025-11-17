import logging
import os
import subprocess
import time
import json
import threading

LOG_DIR = "logs"
CONFIG_DIR = "config"
LOG_FILE = os.path.join(LOG_DIR, "scheduler.log")
STATS_FILE = os.path.join(CONFIG_DIR, "task_stats.json")

# Lock per garantire l'accesso thread-safe al file delle statistiche
_stats_lock = threading.Lock()

def _load_task_stats():
    """Carica le statistiche dei task da un file JSON in modo thread-safe."""
    with _stats_lock:
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

def _save_task_stats(stats):
    """Salva le statistiche dei task su un file JSON in modo thread-safe."""
    with _stats_lock:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=4)

def update_task_stats(task_path, duration):
    """Aggiorna le statistiche min/max per un dato task."""
    stats = _load_task_stats()
    task_stats = stats.get(task_path, {})

    current_min = task_stats.get('min')
    current_max = task_stats.get('max')

    if current_min is None or duration < current_min:
        task_stats['min'] = duration

    if current_max is None or duration > current_max:
        task_stats['max'] = duration

    stats[task_path] = task_stats
    _save_task_stats(stats)


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

        # Controlla se il task è abilitato. Per retrocompatibilità, se la chiave 'enabled'
        # non esiste, il task viene considerato abilitato.
        if not task.get('enabled', True):
            logging.info(f"[{flow_name}] Task '{task_name}' saltato perché disabilitato.")
            continue

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
                update_task_stats(task_path, duration) # Aggiorna le statistiche
                if i < len(tasks) - 1:
                    next_task_name = tasks[i+1].get('name', 'Task Senza Nome')
                    logging.info(f"[{flow_name}] Prossimo task: '{next_task_name}'")
            else:
                # Se il task fallisce, logga tutto l'output e interrompi il flusso
                logging.error(f"[{flow_name}] ERRORE: Task '{task_name}' terminato con codice {result.returncode} dopo {duration:.2f} secondi.")

                # Logga sia stdout che stderr perché l'errore può finire in entrambi
                if result.stdout:
                    logging.error(f"[{flow_name}] Output standard del task '{task_name}':\n{result.stdout.strip()}")
                if result.stderr:
                    logging.error(f"[{flow_name}] Errore standard del task '{task_name}':\n{result.stderr.strip()}")

                logging.critical(f"[{flow_name}] FLUSSO INTERROTTO a causa di un errore nel task '{task_name}'. I task successivi non verranno eseguiti.")
                break # Interrompe il ciclo for

        except Exception as e:
            logging.critical(f"[{flow_name}] Errore critico durante l'esecuzione del task '{task_name}': {e}")
            logging.warning(f"[{flow_name}] Flusso interrotto a causa di un'eccezione.")
            break

    logging.info(f"Flusso '{flow_name}' terminato.")
