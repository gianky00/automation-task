import tkinter as tk
from tkinter import ttk

class WorkflowPanel(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.create_widgets()

    def create_widgets(self):
        ttk.Label(self, text="Flussi di Lavoro", font=("Arial", 12, "bold")).pack(pady=5)

        self.scheduler_button = ttk.Button(self, text="Avvia Scheduler", command=self.controller.toggle_scheduler)
        self.scheduler_button.pack(fill=tk.X, pady=5)

        workflows_frame = ttk.Frame(self)
        workflows_frame.pack(fill=tk.BOTH, expand=True)
        self.workflows_listbox = tk.Listbox(workflows_frame, exportselection=False)
        self.workflows_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_workflows = ttk.Scrollbar(workflows_frame, orient=tk.VERTICAL, command=self.workflows_listbox.yview)
        scrollbar_workflows.pack(side=tk.RIGHT, fill=tk.Y)
        self.workflows_listbox.config(yscrollcommand=scrollbar_workflows.set)
        self.workflows_listbox.bind("<<ListboxSelect>>", self.controller.details_panel.on_workflow_select)

        btn_frame_workflows = ttk.Frame(self)
        btn_frame_workflows.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame_workflows, text="Aggiungi Nuovo", command=self.controller.details_panel.add_new_workflow).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(btn_frame_workflows, text="Rimuovi", command=self.controller.details_panel.delete_selected_workflow).pack(side=tk.LEFT, expand=True, fill=tk.X)
