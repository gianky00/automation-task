import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import xml.etree.ElementTree as ET
import re

CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "workflows.json")


def parse_task_xml(filepath):
    """
    Estrae i dati di un flusso da un file XML dell'Utilità di Pianificazione di Windows.
    Solleva eccezioni in caso di errori di parsing o dati mancanti.
    """
    # Gestione del namespace
    namespaces = {'win': 'http://schemas.microsoft.com/windows/2004/02/mit/task'}
    tree = ET.parse(filepath)
    root = tree.getroot()

    # Estrazione dei dati
    description_node = root.find('win:RegistrationInfo/win:Description', namespaces)
    flow_name = description_node.text.strip() if description_node is not None and description_node.text else "Flusso Importato"

    start_boundary_node = root.find('win:Triggers/win:CalendarTrigger/win:StartBoundary', namespaces)
    if start_boundary_node is None:
        raise ValueError("Impossibile trovare 'StartBoundary' nel trigger. Assicurarsi che sia un trigger basato su calendario.")

    time_str = start_boundary_node.text.split('T')[1]
    schedule_time = f"{time_str.split(':')[0]}:{time_str.split(':')[1]}"

    days_of_week_node = root.find('win:Triggers/win:CalendarTrigger/win:ScheduleByWeek/win:DaysOfWeek', namespaces)
    schedule_days = []
    if days_of_week_node is not None:
        day_map = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6}
        for day_node in days_of_week_node:
            day_name = day_node.tag.replace(f"{{{namespaces['win']}}}", "")
            if day_name in day_map:
                schedule_days.append(day_map[day_name])

    arguments_node = root.find('win:Actions/win:Exec/win:Arguments', namespaces)
    if arguments_node is None or not arguments_node.text:
        raise ValueError("Impossibile trovare il percorso dello script negli argomenti dell'azione.")

    match = re.search(r'["\'](.*\.py)["\']', arguments_node.text)
    if not match:
        raise ValueError("Nessun file .py trovato negli argomenti. L'argomento deve contenere il percorso a uno script Python.")
    task_path = match.group(1)

    return {
        "name": flow_name,
        "data": {
            "tasks": [task_path],
            "schedule_time": schedule_time,
            "schedule_days": sorted(schedule_days)
        }
    }


class WorkflowConfiguratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Configuratore Flussi di Lavoro")
        self.root.geometry("900x600")

        self.workflows = {}
        self.selected_workflow_name = None

        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.load_workflows()
        self.create_widgets()
        self.populate_workflows_list()

    def load_workflows(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                self.workflows = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.workflows = {}

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
        ttk.Separator(left_pane, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Button(left_pane, text="Importa da XML...", command=self.import_from_xml).pack(fill=tk.X)

        details_frame = ttk.LabelFrame(right_pane, text="Dettagli Flusso", padding="10")
        details_frame.pack(fill=tk.BOTH, expand=True)
        name_frame = ttk.Frame(details_frame)
        name_frame.pack(fill=tk.X, pady=5)
        ttk.Label(name_frame, text="Nome Flusso:", width=15).pack(side=tk.LEFT)
        self.flow_name_entry = ttk.Entry(name_frame)
        self.flow_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tasks_frame = ttk.LabelFrame(details_frame, text="Task Sequenziali (.py)")
        tasks_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.tasks_listbox = tk.Listbox(tasks_frame)
        self.tasks_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        task_buttons_frame = ttk.Frame(tasks_frame)
        task_buttons_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        ttk.Button(task_buttons_frame, text="Aggiungi Task", command=self.add_task).pack(fill=tk.X, pady=2)
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
        save_button = ttk.Button(right_pane, text="SALVA TUTTE LE MODIFICHE", command=self.save_workflows)
        save_button.pack(fill=tk.X, pady=10)

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
        for task in flow_data.get("tasks", []):
            self.tasks_listbox.insert(tk.END, task)
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
        current_data = {
            "tasks": list(self.tasks_listbox.get(0, tk.END)),
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

    def import_from_xml(self):
        filepath = filedialog.askopenfilename(
            title="Seleziona il file XML dell'Utilità di Pianificazione",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if not filepath: return
        try:
            imported_flow = parse_task_xml(filepath)
            flow_name = imported_flow["name"]

            original_flow_name = flow_name
            i = 1
            while flow_name in self.workflows:
                flow_name = f"{original_flow_name} ({i})"
                i += 1

            self.workflows[flow_name] = imported_flow["data"]
            self.populate_workflows_list()
            messagebox.showinfo("Successo", f"Flusso '{flow_name}' importato con successo!")

        except (ET.ParseError, ValueError) as e:
            messagebox.showerror("Errore di Importazione", f"Impossibile importare il file:\n{e}")
        except Exception as e:
            messagebox.showerror("Errore Inatteso", f"Si è verificato un errore: {e}")

    def add_task(self):
        filepaths = filedialog.askopenfilenames(title="Seleziona script Python", filetypes=[("Python files", "*.py"), ("All files", "*.*")])
        for filepath in filepaths:
            try:
                rel_path = os.path.relpath(filepath)
                self.tasks_listbox.insert(tk.END, rel_path)
            except ValueError:
                self.tasks_listbox.insert(tk.END, filepath)

    def remove_task(self):
        selected_indices = self.tasks_listbox.curselection()
        if not selected_indices: return
        for i in sorted(selected_indices, reverse=True):
            self.tasks_listbox.delete(i)

    def move_task_up(self):
        selected_indices = self.tasks_listbox.curselection()
        if not selected_indices: return
        for i in selected_indices:
            if i > 0:
                text = self.tasks_listbox.get(i)
                self.tasks_listbox.delete(i)
                self.tasks_listbox.insert(i - 1, text)
                self.tasks_listbox.selection_set(i - 1)

    def move_task_down(self):
        selected_indices = self.tasks_listbox.curselection()
        if not selected_indices: return
        for i in sorted(selected_indices, reverse=True):
            if i < self.tasks_listbox.size() - 1:
                text = self.tasks_listbox.get(i)
                self.tasks_listbox.delete(i)
                self.tasks_listbox.insert(i + 1, text)
                self.tasks_listbox.selection_set(i + 1)

if __name__ == "__main__":
    root = tk.Tk()
    app = WorkflowConfiguratorApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.save_workflows(), root.destroy()))
    root.mainloop()
