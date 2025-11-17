import tkinter as tk
from tkinter import ttk, scrolledtext
import queue
import logging

class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))

class LogViewer(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.log_queue = queue.Queue()
        self.queue_handler = QueueHandler(self.log_queue)
        logging.getLogger().addHandler(self.queue_handler)

        self.create_widgets()
        self.poll_log_queue()

    def create_widgets(self):
        log_frame = ttk.LabelFrame(self, text="Log di Esecuzione", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_widget = scrolledtext.ScrolledText(log_frame, state='disabled', wrap=tk.WORD, height=10)
        self.log_widget.pack(fill=tk.BOTH, expand=True)

    def display_log_record(self, record):
        self.log_widget.configure(state='normal')
        self.log_widget.insert(tk.END, record + '\n')
        self.log_widget.configure(state='disabled')
        self.log_widget.yview(tk.END)

    def poll_log_queue(self):
        while True:
            try:
                record = self.log_queue.get(block=False)
                self.display_log_record(record)
            except queue.Empty:
                break
        self.after(100, self.poll_log_queue)

    def clear_logs(self):
        self.log_widget.configure(state='normal')
        self.log_widget.delete('1.0', tk.END)
        self.log_widget.configure(state='disabled')
