import tkinter as tk
from tkinter import ttk, messagebox
import logging
import os
import signal
import subprocess
import json
from datetime import datetime, timedelta

from core_logic import setup_logging
from .components.workflow_panel import WorkflowPanel
from .components.details_panel import DetailsPanel
from .components.log_viewer import LogViewer

CONFIG_DIR = "config"
STATUS_FILE = os.path.join(CONFIG_DIR, "scheduler_status.json")

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Configuratore Flussi di Lavoro")
        self.geometry("900x750")

        self.workflows = {}
        self.selected_workflow_name = None

        setup_logging()

        self.create_widgets()
        self.update_status_bar()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        try:
            self.details_panel._save_workflows_to_file()
        except Exception as e:
            logging.error(f"Errore durante il salvataggio automatico alla chiusura: {e}")
            if not messagebox.askyesno(
                "Errore di Salvataggio",
                "Impossibile salvare le modifiche. Chiudere comunque l'applicazione?\n"
                "Eventuali modifiche non salvate andranno perse."
            ):
                return
        self.destroy()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.workflow_panel = WorkflowPanel(main_frame, self)
        self.workflow_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self.details_panel = DetailsPanel(main_frame, self)
        self.details_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.log_viewer = LogViewer(self, height=10)
        self.log_viewer.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.status_bar = ttk.Label(self, text="Stato Scheduler: Inizializzazione...", anchor=tk.W, relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _get_scheduler_status(self):
        try:
            with open(STATUS_FILE, 'r') as f:
                status_data = json.load(f)
            pid = status_data.get('pid')
            if not pid:
                return {'status': 'stopped', 'pid': None}
            last_update = datetime.fromisoformat(status_data.get('timestamp'))
            if datetime.now() - last_update > timedelta(seconds=15):
                return {'status': 'timeout', 'pid': pid}
            return {'status': 'running', 'pid': pid, 'data': status_data}
        except (FileNotFoundError, json.JSONDecodeError):
            return {'status': 'stopped', 'pid': None}

    def toggle_scheduler(self):
        status_info = self._get_scheduler_status()
        status = status_info.get('status')
        pid = status_info.get('pid')

        if status in ['running', 'timeout']:
            confirm_msg = "Sei sicuro di voler fermare lo scheduler?"
            if status == 'timeout':
                confirm_msg = "Lo scheduler sembra non rispondere. Sei sicuro di voler forzare l'arresto?"
            if messagebox.askyesno("Conferma", confirm_msg):
                if pid:
                    try:
                        os.kill(pid, signal.SIGTERM)
                        logging.info(f"Segnale di terminazione inviato allo scheduler (PID: {pid}).")
                    except (ProcessLookupError, PermissionError) as e:
                        logging.error(f"Impossibile terminare il processo {pid}: {e}.")
                if os.path.exists(STATUS_FILE):
                    try:
                        os.remove(STATUS_FILE)
                    except OSError as e:
                        logging.error(f"Impossibile rimuovere il file di stato: {e}")
        else:
            try:
                self.details_panel._save_workflows_to_file()
                command = ["pythonw", "scheduler_service.py"]
                subprocess.Popen(command, creationflags=subprocess.DETACHED_PROCESS)
                logging.info("Avvio dello scheduler in background...")
            except Exception as e:
                logging.error(f"Impossibile avviare lo scheduler: {e}")
                messagebox.showerror("Errore", f"Impossibile avviare il servizio scheduler:\n{e}")
        self.update_status_bar()

    def update_status_bar(self):
        status_info = self._get_scheduler_status()
        status = status_info.get('status')
        status_text = "Stato Scheduler: "
        if status == 'running':
            running_flows = status_info.get('data', {}).get('running_flows', [])
            status_text += f"IN ESECUZIONE ({len(running_flows)} flussi)" if running_flows else "IN ESECUZIONE (in attesa)"
            status_color = "blue" if running_flows else "green"
            self.workflow_panel.scheduler_button.config(text="Ferma Scheduler")
        elif status == 'timeout':
            status_text += "NON RISPONDE"
            status_color = "orange"
            self.workflow_panel.scheduler_button.config(text="Forza Arresto")
        else:
            status_text += "FERMATO"
            status_color = "red"
            self.workflow_panel.scheduler_button.config(text="Avvia Scheduler")
        self.status_bar.config(text=status_text, foreground=status_color)
        self.after(2000, self.update_status_bar)
