import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import xml.etree.ElementTree as ET
import re
import threading
import logging
from core_logic import execute_flow
from utils import format_duration

CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "workflows.json")
STATS_FILE = os.path.join(CONFIG_DIR, "task_stats.json")

class DetailsPanel(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.current_tasks = []
        self.task_stats = self.load_task_stats()

        self.create_widgets()
        self.load_workflows()
        self.populate_workflows_list()

    def create_widgets(self):
        details_frame = ttk.LabelFrame(self, text="Dettagli Flusso", padding="10")
        details_frame.pack(fill=tk.BOTH, expand=True)
        name_frame = ttk.Frame(details_frame)
        name_frame.pack(fill=tk.X, pady=5)
        ttk.Label(name_frame, text="Nome Flusso:", width=15).pack(side=tk.LEFT)
        self.flow_name_var = tk.StringVar()
        self.flow_name_entry = ttk.Entry(name_frame, textvariable=self.flow_name_var)
        self.flow_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.flow_name_entry.bind("<FocusOut>", self.on_workflow_name_change)
        self.flow_name_entry.bind("<Return>", self.on_workflow_name_change)
        tasks_frame = ttk.LabelFrame(details_frame, text="Task Sequenziali (doppio click per modificare)")
        tasks_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.tasks_tree = ttk.Treeview(tasks_frame, columns=("task_name", "min_time", "max_time"), show="headings")
        self.tasks_tree.heading("task_name", text="Task")
        self.tasks_tree.heading("min_time", text="Tempo Min")
        self.tasks_tree.heading("max_time", text="Tempo Max")
        self.tasks_tree.column("task_name", width=400)
        self.tasks_tree.column("min_time", width=100, anchor=tk.E)
        self.tasks_tree.column("max_time", width=100, anchor=tk.E)
        self.tasks_tree.tag_configure('disabled', foreground='gray', font=('Arial', 10, 'overstrike'))
        self.tasks_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tasks_tree.bind("<Double-1>", self.edit_selected_task)

        task_buttons_frame = ttk.Frame(tasks_frame)
        task_buttons_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        ttk.Button(task_buttons_frame, text="Aggiungi Task", command=self.add_task).pack(fill=tk.X, pady=2)
        ttk.Button(task_buttons_frame, text="Importa Task da XML...", command=self.import_task_from_xml).pack(fill=tk.X, pady=2)
        ttk.Button(task_buttons_frame, text="Importa da Cartella...", command=self.import_tasks_from_folder).pack(fill=tk.X, pady=2)
        ttk.Button(task_buttons_frame, text="Rimuovi Task", command=self.remove_task).pack(fill=tk.X, pady=2)
        ttk.Separator(task_buttons_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        ttk.Button(task_buttons_frame, text="Abilita/Disabilita Task", command=self.toggle_task_enabled).pack(fill=tk.X, pady=2)
        ttk.Separator(task_buttons_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        ttk.Button(task_buttons_frame, text="Sposta Su", command=self.move_task_up).pack(fill=tk.X, pady=2)
        ttk.Button(task_buttons_frame, text="Sposta Giù", command=self.move_task_down).pack(fill=tk.X, pady=2)

        schedule_frame = ttk.LabelFrame(details_frame, text="Pianificazione")
        schedule_frame.pack(fill=tk.X, pady=10)
        time_frame = ttk.Frame(schedule_frame)
        time_frame.pack(pady=5)
        ttk.Label(time_frame, text="Esegui alle ore:").pack(side=tk.LEFT, padx=5)
        self.hour_spinbox = ttk.Spinbox(time_frame, from_=0, to=23, width=5, format="%02.0f", command=self._save_workflows_to_file)
        self.hour_spinbox.pack(side=tk.LEFT)
        ttk.Label(time_frame, text=":").pack(side=tk.LEFT)
        self.minute_spinbox = ttk.Spinbox(time_frame, from_=0, to=59, width=5, format="%02.0f", command=self._save_workflows_to_file)
        self.minute_spinbox.pack(side=tk.LEFT)
        days_frame = ttk.Frame(schedule_frame)
        days_frame.pack(pady=5)
        ttk.Label(days_frame, text="Nei giorni:").pack(side=tk.LEFT, padx=5)
        self.day_vars = [tk.BooleanVar() for _ in range(7)]
        days = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
        for i, day in enumerate(days):
            ttk.Checkbutton(days_frame, text=day, variable=self.day_vars[i], command=self._save_workflows_to_file).pack(side=tk.LEFT)

        action_frame = ttk.Frame(self)
        action_frame.pack(fill=tk.X, pady=10)
        ttk.Button(action_frame, text="Esegui Flusso", command=self.run_workflow_now).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        ttk.Button(action_frame, text="Esegui Task Selezionato", command=self.run_selected_task).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

    def load_workflows(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                self.controller.workflows = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.controller.workflows = {}

    def load_task_stats(self):
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_workflows_to_file(self):
        if self.controller.selected_workflow_name:
            self.update_workflow_from_ui(self.controller.selected_workflow_name)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.controller.workflows, f, indent=4)

    def populate_workflows_list(self):
        self.controller.workflow_panel.workflows_listbox.delete(0, tk.END)
        for name in sorted(self.controller.workflows.keys()):
            self.controller.workflow_panel.workflows_listbox.insert(tk.END, name)

    def on_workflow_select(self, event):
        selection_indices = self.controller.workflow_panel.workflows_listbox.curselection()
        if not selection_indices: return
        if self.controller.selected_workflow_name:
            self.update_workflow_from_ui(self.controller.selected_workflow_name)
        selected_index = selection_indices[0]
        self.controller.selected_workflow_name = self.controller.workflow_panel.workflows_listbox.get(selected_index)
        self.populate_workflow_details(self.controller.selected_workflow_name)

    def populate_workflow_details(self, flow_name):
        self.clear_details_panel()
        flow_data = self.controller.workflows.get(flow_name)
        if not flow_data: return

        self.flow_name_var.set(flow_name)
        self.current_tasks = flow_data.get("tasks", [])

        for i in self.tasks_tree.get_children():
            self.tasks_tree.delete(i)

        self.task_stats = self.load_task_stats()

        for task in self.current_tasks:
            task_path = task.get('path', '')
            task_name = task.get('name', 'Task Senza Nome')
            stats = self.task_stats.get(task_path, {})
            min_t = format_duration(stats.get('min'))
            max_t = format_duration(stats.get('max'))
            tags = () if task.get('enabled', True) else ('disabled',)
            self.tasks_tree.insert("", tk.END, values=(task_name, min_t, max_t), tags=tags)

        hour, minute = map(int, flow_data.get("schedule_time", "00:00").split(':'))
        self.hour_spinbox.set(f"{hour:02}")
        self.minute_spinbox.set(f"{minute:02}")
        selected_days = flow_data.get("schedule_days", [])
        for i in range(7):
            self.day_vars[i].set(i in selected_days)

    def update_workflow_from_ui(self, flow_name):
        if flow_name not in self.controller.workflows: return
        new_flow_name = self.flow_name_entry.get().strip()
        if not new_flow_name: return

        current_data = {
            "tasks": self.current_tasks,
            "schedule_time": f"{int(self.hour_spinbox.get()):02}:{int(self.minute_spinbox.get()):02}",
            "schedule_days": [i for i, var in enumerate(self.day_vars) if var.get()]
        }
        if new_flow_name != flow_name:
            self.controller.workflows[new_flow_name] = current_data
            del self.controller.workflows[flow_name]
            self.controller.selected_workflow_name = new_flow_name
        else:
            self.controller.workflows[flow_name] = current_data

    def clear_details_panel(self):
        self.flow_name_entry.delete(0, tk.END)
        for i in self.tasks_tree.get_children():
            self.tasks_tree.delete(i)
        self.current_tasks = []
        self.hour_spinbox.set("00")
        self.minute_spinbox.set("00")
        for var in self.day_vars: var.set(False)

    def add_new_workflow(self):
        i = 1
        while f"Nuovo Flusso {i}" in self.controller.workflows: i += 1
        new_name = f"Nuovo Flusso {i}"
        self.controller.workflows[new_name] = {"tasks": [], "schedule_time": "09:00", "schedule_days": []}
        self._save_workflows_to_file()
        self.populate_workflows_list()
        self.controller.workflow_panel.workflows_listbox.selection_set(tk.END)
        self.on_workflow_select(None)

    def delete_selected_workflow(self):
        if not self.controller.selected_workflow_name:
            messagebox.showwarning("Attenzione", "Nessun flusso selezionato.")
            return
        if messagebox.askyesno("Conferma", f"Sei sicuro di voler eliminare il flusso '{self.controller.selected_workflow_name}'?"):
            del self.controller.workflows[self.controller.selected_workflow_name]
            self.controller.selected_workflow_name = None
            self._save_workflows_to_file()
            self.clear_details_panel()
            self.populate_workflows_list()

    def run_workflow_now(self):
        if not self.controller.selected_workflow_name:
            messagebox.showwarning("Azione non permessa", "Seleziona un flusso di lavoro da eseguire.")
            return
        flow_name = self.controller.selected_workflow_name
        tasks = self.current_tasks
        if not tasks:
            messagebox.showinfo("Informazione", f"Il flusso '{flow_name}' non ha task da eseguire.")
            return
        self.controller.log_viewer.clear_logs()
        execution_thread = threading.Thread(target=execute_flow, args=(f"{flow_name} (Manuale)", tasks))
        execution_thread.daemon = True
        execution_thread.start()

    def run_selected_task(self):
        selected_items = self.tasks_tree.selection()
        if not selected_items:
            messagebox.showwarning("Azione non permessa", "Seleziona un task da eseguire.")
            return
        if len(selected_items) > 1:
            messagebox.showwarning("Azione non permessa", "Puoi eseguire solo un task alla volta.")
            return
        index = self.tasks_tree.index(selected_items[0])
        task_data = self.current_tasks[index]
        task_name = task_data.get('name', 'Task Senza Nome')
        self.controller.log_viewer.clear_logs()
        execution_thread = threading.Thread(target=execute_flow, args=(f"Task Singolo: {task_name}", [task_data]))
        execution_thread.daemon = True
        execution_thread.start()

    def add_task(self):
        filepaths = filedialog.askopenfilenames(
            title="Seleziona Script",
            filetypes=[("Script Supportati", "*.py *.bat *.ps1"), ("All files", "*.*")]
        )
        if not filepaths: return
        for filepath in filepaths:
            try:
                task_path = os.path.relpath(filepath)
            except ValueError:
                task_path = filepath
            task_name = os.path.splitext(os.path.basename(task_path))[0]
            new_task = {'name': task_name, 'path': task_path, 'enabled': True}
            self.current_tasks.append(new_task)
            self.tasks_tree.insert("", tk.END, values=(new_task['name'], "", ""))
        self._save_workflows_to_file()
        messagebox.showinfo("Successo", f"{len(filepaths)} task aggiunti con successo.")

    def remove_task(self):
        selected_items = self.tasks_tree.selection()
        if not selected_items: return
        indices_to_remove = sorted([self.tasks_tree.index(item) for item in selected_items], reverse=True)
        for index in indices_to_remove:
            self.current_tasks.pop(index)
        for item in selected_items:
            self.tasks_tree.delete(item)
        if selected_items:
            self._save_workflows_to_file()

    def toggle_task_enabled(self):
        selected_items = self.tasks_tree.selection()
        if not selected_items:
            messagebox.showwarning("Azione non permessa", "Seleziona almeno un task da abilitare o disabilitare.")
            return
        for item in selected_items:
            index = self.tasks_tree.index(item)
            task_data = self.current_tasks[index]
            is_currently_enabled = task_data.get('enabled', True)
            task_data['enabled'] = not is_currently_enabled
        if selected_items:
            self._save_workflows_to_file()
        self.populate_workflow_details(self.controller.selected_workflow_name)

    def move_task_up(self):
        selected_items = self.tasks_tree.selection()
        if not selected_items: return
        for item in selected_items:
            index = self.tasks_tree.index(item)
            if index > 0:
                self.tasks_tree.move(item, "", index - 1)
                task_data = self.current_tasks.pop(index)
                self.current_tasks.insert(index - 1, task_data)
        if selected_items:
            self._save_workflows_to_file()

    def move_task_down(self):
        selected_items = self.tasks_tree.selection()
        if not selected_items: return
        for item in reversed(selected_items):
            index = self.tasks_tree.index(item)
            if index < len(self.current_tasks) - 1:
                self.tasks_tree.move(item, "", index + 1)
                task_data = self.current_tasks.pop(index)
                self.current_tasks.insert(index + 1, task_data)
        if selected_items:
            self._save_workflows_to_file()

    def edit_selected_task(self, event=None):
        selected_items = self.tasks_tree.selection()
        if not selected_items: return
        item = selected_items[0]
        index = self.tasks_tree.index(item)
        task_data = self.current_tasks[index]

        dialog = tk.Toplevel(self.controller)
        dialog.title("Modifica Task")
        dialog.geometry("600x150")
        dialog.transient(self.controller)
        dialog.grab_set()

        ttk.Label(dialog, text="Nome del Task:").pack(padx=10, pady=(10, 0))
        name_var = tk.StringVar(value=task_data['name'])
        name_entry = ttk.Entry(dialog, textvariable=name_var)
        name_entry.pack(padx=10, pady=2, fill=tk.X, expand=True)
        name_entry.focus_set()
        name_entry.selection_range(0, tk.END)

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
            self.current_tasks[index]['name'] = new_name
            self.current_tasks[index]['path'] = new_path
            self.tasks_tree.item(item, values=(new_name, self.tasks_tree.item(item, 'values')[1], self.tasks_tree.item(item, 'values')[2]))
            self._save_workflows_to_file()
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Annulla", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        dialog.bind("<Return>", lambda e: on_ok())
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        self.controller.wait_window(dialog)

    def on_workflow_name_change(self, event=None):
        if not self.controller.selected_workflow_name: return
        new_name = self.flow_name_var.get().strip()
        old_name = self.controller.selected_workflow_name
        if not new_name or new_name == old_name:
            self.flow_name_var.set(old_name)
            return
        if new_name in self.controller.workflows:
            messagebox.showwarning("Nome Duplicato", f"Un flusso di lavoro con il nome '{new_name}' esiste già.")
            self.flow_name_var.set(old_name)
            return
        self.update_workflow_from_ui(old_name)
        self._save_workflows_to_file()
        self.populate_workflows_list()
        try:
            sorted_workflows = sorted(self.controller.workflows.keys())
            new_index = sorted_workflows.index(new_name)
            self.controller.workflow_panel.workflows_listbox.selection_set(new_index)
            self.controller.workflow_panel.workflows_listbox.activate(new_index)
            self.controller.workflow_panel.workflows_listbox.see(new_index)
        except ValueError:
            logging.warning(f"Impossibile trovare il flusso rinominato '{new_name}' nella lista.")

    def import_task_from_xml(self):
        if not self.controller.selected_workflow_name:
            messagebox.showwarning("Azione non permessa", "Seleziona prima un flusso di lavoro a cui aggiungere il task.")
            return
        filepath = filedialog.askopenfilename(
            title="Seleziona il file XML del Task da importare",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if not filepath: return
        try:
            task_path = self._parse_task_path_from_xml(filepath)
            task_name = os.path.splitext(os.path.basename(filepath))[0]
            new_task = {'name': task_name, 'path': task_path, 'enabled': True}
            self.current_tasks.append(new_task)
            self.tasks_tree.insert("", tk.END, values=(new_task['name'], "", ""))
            self._save_workflows_to_file()
            messagebox.showinfo("Successo", f"Task '{task_name}' importato e aggiunto al flusso.")
        except (ET.ParseError, ValueError) as e:
            messagebox.showerror("Errore di Importazione", f"Impossibile importare il task:\n{e}")
        except Exception as e:
            messagebox.showerror("Errore Inatteso", f"Si è verificato un errore: {e}")

    def import_tasks_from_folder(self):
        if not self.controller.selected_workflow_name:
            messagebox.showwarning("Azione non permessa", "Seleziona prima un flusso di lavoro a cui aggiungere i task.")
            return
        folder_path = filedialog.askdirectory(title="Seleziona una cartella contenente file XML")
        if not folder_path: return
        success_count = 0
        ignored_files = []
        for filename in os.listdir(folder_path):
            filepath = os.path.join(folder_path, filename)
            if filename.lower().endswith(".xml"):
                try:
                    task_path = self._parse_task_path_from_xml(filepath)
                    task_name = os.path.splitext(filename)[0]
                    new_task = {'name': task_name, 'path': task_path, 'enabled': True}
                    self.current_tasks.append(new_task)
                    self.tasks_tree.insert("", tk.END, values=(new_task['name'], "", ""))
                    success_count += 1
                except (ET.ParseError, ValueError) as e:
                    ignored_files.append({'file': filename, 'reason': str(e)})
                except Exception as e:
                    ignored_files.append({'file': filename, 'reason': f"Errore inatteso: {e}"})
            else:
                if os.path.isfile(filepath):
                    ignored_files.append({'file': filename, 'reason': 'File non XML'})
        if success_count > 0:
            self._save_workflows_to_file()
        self.show_import_report(success_count, ignored_files)

    def show_import_report(self, success_count, ignored_files):
        dialog = tk.Toplevel(self.controller)
        dialog.title("Report di Importazione")
        dialog.geometry("600x400")
        dialog.transient(self.controller)
        dialog.grab_set()

        summary_frame = ttk.Frame(dialog, padding="10")
        summary_frame.pack(fill=tk.X)
        ttk.Label(summary_frame, text=f"Task aggiunti con successo: {success_count}", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(summary_frame, text=f"File ignorati o non validi: {len(ignored_files)}", font=("Arial", 10, "bold")).pack(anchor=tk.W)

        if ignored_files:
            details_frame = ttk.LabelFrame(dialog, text="Dettagli File Ignorati", padding="10")
            details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            report_text = tk.scrolledtext.ScrolledText(details_frame, wrap=tk.WORD, height=15)
            report_text.pack(fill=tk.BOTH, expand=True)
            for item in ignored_files:
                report_text.insert(tk.END, f"File: {item['file']}\nMotivo: {item['reason']}\n\n")
            report_text.configure(state='disabled')

        ttk.Button(dialog, text="OK", command=dialog.destroy).pack(pady=10)
        dialog.bind("<Return>", lambda e: dialog.destroy())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    def _parse_task_path_from_xml(self, filepath):
        namespaces = {'win': 'http://schemas.microsoft.com/windows/2004/02/mit/task'}
        tree = ET.parse(filepath)
        root = tree.getroot()
        exec_node = root.find('win:Actions/win:Exec', namespaces)
        if exec_node is None:
            raise ValueError("Nodo <Exec> non trovato nel file XML.")
        arguments_node = exec_node.find('win:Arguments', namespaces)
        command_node = exec_node.find('win:Command', namespaces)
        if arguments_node is not None and arguments_node.text:
            match = re.search(r'["\'](.*?\.(?:py|bat|ps1))["\']', arguments_node.text, re.IGNORECASE)
            if match:
                return match.group(1)
        if command_node is not None and command_node.text:
            match = re.search(r'["\']?(.*?\.(?:py|bat|ps1))["\']?', command_node.text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        raise ValueError("Nessun percorso di script supportato (.py, .bat, .ps1) trovato.")
