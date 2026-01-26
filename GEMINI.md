# Automation Task Project Context

## Project Overview
This project is a **Sequential Task Scheduler** application built with Python. It allows users to create, schedule, and execute workflows consisting of multiple tasks (Python scripts, Batch files, PowerShell scripts) that run in a strict sequence.

**Key Technologies:**
- **Language:** Python 3.x (Standard Library only - "Zero Dependency").
- **GUI:** Tkinter (`gui_configurator.py`).
- **Persistence:** JSON files (`config/workflows.json`, `config/scheduler_status.json`, `config/task_stats.json`).
- **Concurrency:** Threading for non-blocking GUI and background execution.

**Architecture:**
- **Core Logic (`core_logic.py`):** Contains shared utilities for logging, absolute path resolution (`pathlib`), and **atomic file I/O** (`safe_save_json`, `safe_load_json`) to prevent data corruption.
- **GUI Configurator (`gui_configurator.py`):** The main user interface for managing workflows and manually triggering tasks. It can also start/stop the background scheduler service.
- **Scheduler Service (`scheduler_service.py`):** A background process that monitors the schedule and executes workflows at the configured times.

## Building and Running

### Prerequisites
- Python 3.x installed and added to PATH.
- No external `pip` packages are required.

### Running the Application (Windows)
1.  **GUI Configurator:**
    Run the provided batch script to start the GUI:
    ```batch
    start_gui.bat
    ```
    Alternatively, run directly with Python (or `pythonw` to hide console):
    ```bash
    python gui_configurator.py
    ```

2.  **Scheduler Service:**
    The Scheduler is typically managed directly from the GUI ("Avvia Scheduler" button). It runs as a detached background process using `pythonw`.
    To run it manually for debugging:
    ```bash
    python scheduler_service.py
    ```

### Testing
To run the unit tests and the concurrency stress test:
```bash
python -m unittest discover tests
python tests/verify_concurrency.py
```

## Development Conventions

- **Zero Dependency:** Do not introduce external library dependencies (e.g., `requests`, `pandas`) unless absolutely necessary and approved. Stick to the Python Standard Library.
- **Absolute Paths:** All file paths (logs, config, tasks) must be resolved absolutely relative to `BASE_DIR` in `core_logic.py` to ensure the application works regardless of the working directory (e.g., when launched via Task Scheduler).
- **Atomic I/O:** **ALWAYS** use `safe_save_json` and `safe_load_json` from `core_logic.py` when reading/writing JSON configuration files to prevent race conditions and file corruption.
- **Logging:** Use the centralized logging setup in `core_logic.py`. Logs are written to `logs/scheduler.log`.
- **Task Execution:** Tasks are executed using `subprocess.run`. Ensure new task types (if added) are handled securely.

## Directory Structure
- `config/`: JSON configuration and status files.
- `logs/`: Application logs.
- `tasks/`: Example or user-defined task scripts.
- `tests/`: Unit and integration tests.
- `ui/`: (Legacy/Unused) Directory structure implies potential separation, but currently main GUI logic is in `gui_configurator.py`.
