import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
import xml.etree.ElementTree as ET
import re
import threading
import queue
import logging
from datetime import datetime, timedelta
from core_logic import setup_logging, execute_flow

CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "workflows.json")
STATUS_FILE = os.path.join(CONFIG_DIR, "scheduler_status.json")
STATS_FILE = os.path.join(CONFIG_DIR, "task_stats.json")


class QueueHandler(logging.Handler):
    """Classe per inviare i record di logging a una coda."""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))


def _parse_task_path_from_xml(filepath):
    """
    Estrae il percorso di uno script (py, bat, ps1) da un file XML
    dell'Utilità di Pianificazione di Windows. Cerca prima in <Arguments>
    e poi in <Command> come fallback. Solleva eccezioni in caso di errori.
    """
    namespaces = {'win': 'http://schemas.microsoft.com/windows/2004/02/mit/task'}
    tree = ET.parse(filepath)
    root = tree.getroot()

    exec_node = root.find('win:Actions/win:Exec', namespaces)
    if exec_node is None:
        raise ValueError("Nodo <Exec> non trovato nel file XML.")

    arguments_node = exec_node.find('win:Arguments', namespaces)
    command_node = exec_node.find('win:Command', namespaces)

    # Tenta di trovare il percorso prima negli argomenti
    if arguments_node is not None and arguments_node.text:
        match = re.search(r'["\'](.*?\.(?:py|bat|ps1))["\']', arguments_node.text, re.IGNORECASE)
        if match:
            return match.group(1)

    # Se non trovato, tenta nel comando (fallback)
    if command_node is not None and command_node.text:
        match = re.search(r'["\']?(.*?\.(?:py|bat|ps1))["\']?', command_node.text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    raise ValueError("Nessun percorso di script supportato (.py, .bat, .ps1) trovato in <Arguments> o <Command>.")


def format_duration(seconds):
    """Converte una durata in secondi in una stringa formattata HH:MM:SS.ss."""
    if seconds is None:
        return ""
    try:
        seconds = float(seconds)
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{seconds:05.2f}"
    except (ValueError, TypeError):
        return "Invalido"


class WorkflowConfiguratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Configuratore Flussi di Lavoro")
        self.root.geometry("900x750") # Aumenta l'altezza per i log

        self.workflows = {}
        self.selected_workflow_name = None
        self.current_tasks = [] # Mantiene la lista di dizionari {'name': ..., 'path': ...}

        # 1. Configura il logging di base (file e console)
        os.makedirs(CONFIG_DIR, exist_ok=True)
        setup_logging()

        # 2. Aggiungi l'handler per la GUI
        self.log_queue = queue.Queue()
        self.queue_handler = QueueHandler(self.log_queue)
        logging.getLogger().addHandler(self.queue_handler)

        self.task_stats = self.load_task_stats()
        self.load_workflows()
        self.create_widgets()
        self.populate_workflows_list()

        # Avvia il polling
        self.root.after(100, self.poll_log_queue)
        self.root.after(100, self.update_status_bar) # Avvia subito il primo controllo

    def load_workflows(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                self.workflows = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.workflows = {}

    def load_task_stats(self):
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_workflows(self):
        if self.selected_workflow_name:
            self.update_workflow_from_ui(self.selected_workflow_name)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.workflows, f, indent=4)
        messagebox.showinfo("Successo", "Configurazione di tutti i flussi salvata con successo!")

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        left_pane = ttk.Frame(main_frame, width=250)
        left_pane.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        right_pane = ttk.Frame(main_frame)
        right_pane.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        ttk.Label(left_pane, text="Flussi di Lavoro", font=("Arial", 12, "bold")).pack(pady=5)
        workflows_frame = ttk.Frame(left_pane)
        workflows_frame.pack(fill=tk.BOTH, expand=True)
        self.workflows_listbox = tk.Listbox(workflows_frame, exportselection=False)
        self.workflows_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_workflows = ttk.Scrollbar(workflows_frame, orient=tk.VERTICAL, command=self.workflows_listbox.yview)
        scrollbar_workflows.pack(side=tk.RIGHT, fill=tk.Y)
        self.workflows_listbox.config(yscrollcommand=scrollbar_workflows.set)
        self.workflows_listbox.bind("<<ListboxSelect>>", self.on_workflow_select)

        btn_frame_workflows = ttk.Frame(left_pane)
        btn_frame_workflows.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame_workflows, text="Aggiungi Nuovo", command=self.add_new_workflow).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(btn_frame_workflows, text="Rimuovi", command=self.delete_selected_workflow).pack(side=tk.LEFT, expand=True, fill=tk.X)

        details_frame = ttk.LabelFrame(right_pane, text="Dettagli Flusso", padding="10")
        details_frame.pack(fill=tk.BOTH, expand=True)
        name_frame = ttk.Frame(details_frame)
        name_frame.pack(fill=tk.X, pady=5)
        ttk.Label(name_frame, text="Nome Flusso:", width=15).pack(side=tk.LEFT)
        self.flow_name_entry = ttk.Entry(name_frame)
        self.flow_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tasks_frame = ttk.LabelFrame(details_frame, text="Task Sequenziali (doppio click per modificare)")
        tasks_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.tasks_tree = ttk.Treeview(
            tasks_frame,
            columns=("task_name", "min_time", "max_time"),
            show="headings"
        )
        self.tasks_tree.heading("task_name", text="Task")
        self.tasks_tree.heading("min_time", text="Tempo Min")
        self.tasks_tree.heading("max_time", text="Tempo Max")

        self.tasks_tree.column("task_name", width=400)
        self.tasks_tree.column("min_time", width=100, anchor=tk.E)
        self.tasks_tree.column("max_time", width=100, anchor=tk.E)

        self.tasks_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tasks_tree.bind("<Double-1>", self.edit_selected_task)

        task_buttons_frame = ttk.Frame(tasks_frame)
        task_buttons_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        ttk.Button(task_buttons_frame, text="Aggiungi Task", command=self.add_task).pack(fill=tk.X, pady=2)
        ttk.Button(task_buttons_frame, text="Importa Task da XML...", command=self.import_task_from_xml).pack(fill=tk.X, pady=2)
        ttk.Button(task_buttons_frame, text="Importa da Cartella...", command=self.import_tasks_from_folder).pack(fill=tk.X, pady=2)
        ttk.Button(task_buttons_frame, text="Rimuovi Task", command=self.remove_task).pack(fill=tk.X, pady=2)
        ttk.Separator(task_buttons_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Button(task_buttons_frame, text="Sposta Su", command=self.move_task_up).pack(fill=tk.X, pady=2)
        ttk.Button(task_buttons_frame, text="Sposta Giù", command=self.move_task_down).pack(fill=tk.X, pady=2)

        schedule_frame = ttk.LabelFrame(details_frame, text="Pianificazione")
        schedule_frame.pack(fill=tk.X, pady=10)
        time_frame = ttk.Frame(schedule_frame)
        time_frame.pack(pady=5)
        ttk.Label(time_frame, text="Esegui alle ore:").pack(side=tk.LEFT, padx=5)
        self.hour_spinbox = ttk.Spinbox(time_frame, from_=0, to=23, width=5, format="%02.0f")
        self.hour_spinbox.pack(side=tk.LEFT)
        ttk.Label(time_frame, text=":").pack(side=tk.LEFT)
        self.minute_spinbox = ttk.Spinbox(time_frame, from_=0, to=59, width=5, format="%02.0f")
        self.minute_spinbox.pack(side=tk.LEFT)
        days_frame = ttk.Frame(schedule_frame)
        days_frame.pack(pady=5)
        ttk.Label(days_frame, text="Nei giorni:").pack(side=tk.LEFT, padx=5)
        self.day_vars = [tk.BooleanVar() for _ in range(7)]
        days = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
        for i, day in enumerate(days):
            ttk.Checkbutton(days_frame, text=day, variable=self.day_vars[i]).pack(side=tk.LEFT)

        action_frame = ttk.Frame(right_pane)
        action_frame.pack(fill=tk.X, pady=10)

        run_now_button = ttk.Button(action_frame, text="Esegui Ora", command=self.run_workflow_now)
        run_now_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        save_button = ttk.Button(action_frame, text="SALVA TUTTE LE MODIFICHE", command=self.save_workflows)
        save_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))

        # --- Area Log ---
        log_frame = ttk.LabelFrame(self.root, text="Log di Esecuzione", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.log_widget = scrolledtext.ScrolledText(log_frame, state='disabled', wrap=tk.WORD, height=10)
        self.log_widget.pack(fill=tk.BOTH, expand=True)

        # --- Barra di Stato ---
        self.status_bar = ttk.Label(self.root, text="Stato Scheduler: Inizializzazione...", anchor=tk.W, relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def update_status_bar(self):
        try:
            with open(STATUS_FILE, 'r') as f:
                status_data = json.load(f)

            # Controlla se il timestamp è recente (es. entro gli ultimi 90 secondi)
            last_update = datetime.fromisoformat(status_data.get('timestamp'))
            if datetime.now() - last_update > timedelta(seconds=90):
                status_text = "Stato Scheduler: FERMATO (timeout)"
                status_color = "red"
            else:
                running_flows = status_data.get('running_flows', [])
                if running_flows:
                    status_text = f"Stato Scheduler: IN ESECUZIONE ({len(running_flows)} flussi attivi: {', '.join(running_flows)})"
                    status_color = "blue"
                else:
                    status_text = "Stato Scheduler: IN ESECUZIONE (in attesa)"
                    status_color = "green"

        except (FileNotFoundError, json.JSONDecodeError):
            status_text = "Stato Scheduler: FERMATO"
            status_color = "red"

        self.status_bar.config(text=status_text, foreground=status_color)

        # Ripianifica il controllo
        self.root.after(5000, self.update_status_bar) # Controlla ogni 5 secondi

    def populate_workflows_list(self):
        self.workflows_listbox.delete(0, tk.END)
        for name in sorted(self.workflows.keys()):
            self.workflows_listbox.insert(tk.END, name)

    def on_workflow_select(self, event):
        selection_indices = self.workflows_listbox.curselection()
        if not selection_indices: return
        if self.selected_workflow_name:
            self.update_workflow_from_ui(self.selected_workflow_name)
        selected_index = selection_indices[0]
        self.selected_workflow_name = self.workflows_listbox.get(selected_index)
        self.populate_workflow_details(self.selected_workflow_name)

    def populate_workflow_details(self, flow_name):
        self.clear_details_panel()
        flow_data = self.workflows.get(flow_name)
        if not flow_data: return

        self.flow_name_entry.insert(0, flow_name)
        self.current_tasks = flow_data.get("tasks", [])

        # Pulisci la treeview prima di ripopolarla
        for i in self.tasks_tree.get_children():
            self.tasks_tree.delete(i)

        # Ricarica le statistiche più recenti ogni volta che si seleziona un flusso
        self.task_stats = self.load_task_stats()

        for task in self.current_tasks:
            task_path = task.get('path', '')
            task_name = task.get('name', 'Task Senza Nome')

            stats = self.task_stats.get(task_path, {})
            min_t = format_duration(stats.get('min'))
            max_t = format_duration(stats.get('max'))

            self.tasks_tree.insert("", tk.END, values=(task_name, min_t, max_t))

        hour, minute = map(int, flow_data.get("schedule_time", "00:00").split(':'))
        self.hour_spinbox.set(f"{hour:02}")
        self.minute_spinbox.set(f"{minute:02}")
        selected_days = flow_data.get("schedule_days", [])
        for i in range(7):
            self.day_vars[i].set(i in selected_days)

    def update_workflow_from_ui(self, flow_name):
        if flow_name not in self.workflows: return
        new_flow_name = self.flow_name_entry.get().strip()
        if not new_flow_name: return

        # Salva la lista di dizionari, non solo i nomi
        current_data = {
            "tasks": self.current_tasks,
            "schedule_time": f"{int(self.hour_spinbox.get()):02}:{int(self.minute_spinbox.get()):02}",
            "schedule_days": [i for i, var in enumerate(self.day_vars) if var.get()]
        }
        if new_flow_name != flow_name:
            self.workflows[new_flow_name] = current_data
            del self.workflows[flow_name]
            self.selected_workflow_name = new_flow_name
        else:
            self.workflows[flow_name] = current_data

    def clear_details_panel(self):
        self.flow_name_entry.delete(0, tk.END)
        self.tasks_listbox.delete(0, tk.END)
        self.current_tasks = []
        self.hour_spinbox.set("00")
        self.minute_spinbox.set("00")
        for var in self.day_vars: var.set(False)

    def add_new_workflow(self):
        i = 1
        while f"Nuovo Flusso {i}" in self.workflows: i += 1
        new_name = f"Nuovo Flusso {i}"
        self.workflows[new_name] = {"tasks": [], "schedule_time": "09:00", "schedule_days": []}
        self.populate_workflows_list()
        self.workflows_listbox.selection_set(tk.END)
        self.on_workflow_select(None)

    def delete_selected_workflow(self):
        if not self.selected_workflow_name:
            messagebox.showwarning("Attenzione", "Nessun flusso selezionato.")
            return
        if messagebox.askyesno("Conferma", f"Sei sicuro di voler eliminare il flusso '{self.selected_workflow_name}'?"):
            del self.workflows[self.selected_workflow_name]
            self.selected_workflow_name = None
            self.clear_details_panel()
            self.populate_workflows_list()

    def run_workflow_now(self):
        if not self.selected_workflow_name:
            messagebox.showwarning("Azione non permessa", "Seleziona un flusso di lavoro da eseguire.")
            return

        flow_name = self.selected_workflow_name
        tasks = self.current_tasks

        if not tasks:
            messagebox.showinfo("Informazione", f"Il flusso '{flow_name}' non ha task da eseguire.")
            return

        # Pulisci i log precedenti prima di una nuova esecuzione
        self.log_widget.configure(state='normal')
        self.log_widget.delete('1.0', tk.END)
        self.log_widget.configure(state='disabled')

        # Esegui in un thread per non bloccare la GUI
        execution_thread = threading.Thread(
            target=execute_flow,
            args=(f"{flow_name} (Manuale)", tasks)
        )
        execution_thread.daemon = True # Permette all'app di chiudersi anche se il thread è in esecuzione
        execution_thread.start()

    def import_task_from_xml(self):
        if not self.selected_workflow_name:
            messagebox.showwarning("Azione non permessa", "Seleziona prima un flusso di lavoro a cui aggiungere il task.")
            return

        filepath = filedialog.askopenfilename(
            title="Seleziona il file XML del Task da importare",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if not filepath: return

        try:
            task_path = _parse_task_path_from_xml(filepath)
            # Usa il nome del file (senza estensione) come nome del task
            task_name = os.path.splitext(os.path.basename(filepath))[0]

            new_task = {'name': task_name, 'path': task_path}
            self.current_tasks.append(new_task)
            self.tasks_listbox.insert(tk.END, new_task['name'])

            messagebox.showinfo("Successo", f"Task '{task_name}' importato e aggiunto al flusso.")

        except (ET.ParseError, ValueError) as e:
            messagebox.showerror("Errore di Importazione", f"Impossibile importare il task:\n{e}")
        except Exception as e:
            messagebox.showerror("Errore Inatteso", f"Si è verificato un errore: {e}")

    def import_tasks_from_folder(self):
        if not self.selected_workflow_name:
            messagebox.showwarning("Azione non permessa", "Seleziona prima un flusso di lavoro a cui aggiungere i task.")
            return

        folder_path = filedialog.askdirectory(title="Seleziona una cartella contenente file XML")
        if not folder_path:
            return

        success_count = 0
        ignored_files = [] # Lista per memorizzare i file ignorati e il motivo

        for filename in os.listdir(folder_path):
            filepath = os.path.join(folder_path, filename)
            if filename.lower().endswith(".xml"):
                try:
                    task_path = _parse_task_path_from_xml(filepath)
                    task_name = os.path.splitext(filename)[0]

                    new_task = {'name': task_name, 'path': task_path}
                    self.current_tasks.append(new_task)
                    self.tasks_listbox.insert(tk.END, new_task['name'])
                    success_count += 1
                except (ET.ParseError, ValueError) as e:
                    # Aggiungi il file e il motivo specifico alla lista degli ignorati
                    ignored_files.append({'file': filename, 'reason': str(e)})
                except Exception as e:
                    ignored_files.append({'file': filename, 'reason': f"Errore inatteso: {e}"})
            else:
                # Registra anche i file che non sono XML
                if os.path.isfile(filepath): # Assicurati che sia un file
                    ignored_files.append({'file': filename, 'reason': 'File non XML'})

        self.show_import_report(success_count, ignored_files)


    def show_import_report(self, success_count, ignored_files):
        dialog = tk.Toplevel(self.root)
        dialog.title("Report di Importazione")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()

        summary_frame = ttk.Frame(dialog, padding="10")
        summary_frame.pack(fill=tk.X)

        ttk.Label(summary_frame, text=f"Task aggiunti con successo: {success_count}", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(summary_frame, text=f"File ignorati o non validi: {len(ignored_files)}", font=("Arial", 10, "bold")).pack(anchor=tk.W)

        if ignored_files:
            details_frame = ttk.LabelFrame(dialog, text="Dettagli File Ignorati", padding="10")
            details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            report_text = scrolledtext.ScrolledText(details_frame, wrap=tk.WORD, height=15)
            report_text.pack(fill=tk.BOTH, expand=True)

            # Popola il report
            for item in ignored_files:
                report_text.insert(tk.END, f"File: {item['file']}\nMotivo: {item['reason']}\n\n")

            report_text.configure(state='disabled') # Rendi il testo non modificabile

        ok_button = ttk.Button(dialog, text="OK", command=dialog.destroy)
        ok_button.pack(pady=10)

        dialog.bind("<Return>", lambda e: dialog.destroy())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def add_task(self):
        filepaths = filedialog.askopenfilenames(
            title="Seleziona Script",
            filetypes=[
                ("Script Supportati", "*.py *.bat *.ps1"),
                ("Python files", "*.py"),
                ("Batch files", "*.bat"),
                ("PowerShell files", "*.ps1"),
                ("All files", "*.*")
            ]
        )
        for filepath in filepaths:
            try:
                task_path = os.path.relpath(filepath)
            except ValueError:
                task_path = filepath

            task_name = os.path.splitext(os.path.basename(task_path))[0]
            new_task = {'name': task_name, 'path': task_path}
            self.current_tasks.append(new_task)
            self.tasks_tree.insert("", tk.END, values=(new_task['name'], "", ""))

    def remove_task(self):
        selected_items = self.tasks_tree.selection()
        if not selected_items: return

        # Crea una lista di indici da rimuovere per evitare problemi di mutazione
        indices_to_remove = sorted([self.tasks_tree.index(item) for item in selected_items], reverse=True)

        for index in indices_to_remove:
            self.current_tasks.pop(index)

        # Rimuovi gli elementi dalla Treeview
        for item in selected_items:
            self.tasks_tree.delete(item)


    def move_task_up(self):
        selected_items = self.tasks_tree.selection()
        if not selected_items: return

        for item in selected_items:
            index = self.tasks_tree.index(item)
            if index > 0:
                self.tasks_tree.move(item, "", index - 1)
                # Aggiorna anche la lista dati
                task_data = self.current_tasks.pop(index)
                self.current_tasks.insert(index - 1, task_data)

    def move_task_down(self):
        selected_items = self.tasks_tree.selection()
        if not selected_items: return

        for item in reversed(selected_items): # Muovi dal basso per evitare conflitti di indice
            index = self.tasks_tree.index(item)
            if index < len(self.current_tasks) - 1:
                self.tasks_tree.move(item, "", index + 1)
                # Aggiorna anche la lista dati
                task_data = self.current_tasks.pop(index)
                self.current_tasks.insert(index + 1, task_data)

    def edit_selected_task(self, event=None):
        selected_items = self.tasks_tree.selection()
        if not selected_items:
            return

        item = selected_items[0]
        index = self.tasks_tree.index(item)
        task_data = self.current_tasks[index]

        dialog = tk.Toplevel(self.root)
        dialog.title("Modifica Task")
        dialog.geometry("600x150")
        dialog.transient(self.root)
        dialog.grab_set()

        # Campo Nome
        ttk.Label(dialog, text="Nome del Task:").pack(padx=10, pady=(10, 0))
        name_var = tk.StringVar(value=task_data['name'])
        name_entry = ttk.Entry(dialog, textvariable=name_var)
        name_entry.pack(padx=10, pady=2, fill=tk.X, expand=True)
        name_entry.focus_set()
        name_entry.selection_range(0, tk.END)

        # Campo Percorso
        ttk.Label(dialog, text="Percorso dello Script:").pack(padx=10, pady=(5, 0))
        path_var = tk.StringVar(value=task_data['path'])
        path_entry = ttk.Entry(dialog, textvariable=path_var)
        path_entry.pack(padx=10, pady=2, fill=tk.X, expand=True)

        def on_ok():
            new_name = name_var.get().strip()
            new_path = path_var.get().strip()

            if not new_name or not new_path:
                messagebox.showwarning("Dati non validi", "Nome e percorso non possono essere vuoti.", parent=dialog)
                return

            # Aggiorna sia i dati interni che la listbox
            self.current_tasks[index] = {'name': new_name, 'path': new_path}

            # Ricarica i dettagli del flusso per aggiornare la vista
            self.populate_workflow_details(self.selected_workflow_name)

            # (Opzionale) Prova a riselezionare l'elemento modificato
            children = self.tasks_tree.get_children()
            if index < len(children):
                self.tasks_tree.selection_set(children[index])
                self.tasks_tree.focus(children[index])

            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Annulla", command=on_cancel).pack(side=tk.LEFT, padx=5)

        dialog.bind("<Return>", lambda e: on_ok())
        dialog.bind("<Escape>", lambda e: on_cancel())

        self.root.wait_window(dialog)

    def display_log_record(self, record):
        """Aggiunge un record di log al widget di testo."""
        self.log_widget.configure(state='normal')
        self.log_widget.insert(tk.END, record + '\n')
        self.log_widget.configure(state='disabled')
        self.log_widget.yview(tk.END) # Auto-scroll

    def poll_log_queue(self):
        """Controlla la coda per nuovi log e li visualizza."""
        while True:
            try:
                record = self.log_queue.get(block=False)
                self.display_log_record(record)
            except queue.Empty:
                break
        # Richiama se stessa dopo 100ms
        self.root.after(100, self.poll_log_queue)

if __name__ == "__main__":
    root = tk.Tk()
    app = WorkflowConfiguratorApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.save_workflows(), root.destroy()))
    root.mainloop()
