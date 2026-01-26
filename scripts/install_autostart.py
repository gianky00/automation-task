import sys
import os
import subprocess
from pathlib import Path

def install_task():
    """
    Registra scheduler_service.py come task di Windows che si avvia al Logon.
    """
    # 1. Identifica i percorsi assoluti
    current_script = Path(__file__).resolve()
    project_root = current_script.parent.parent
    service_script = project_root / "scheduler_service.py"
    
    # Verifica esistenza file
    if not service_script.exists():
        print(f"Errore: Non trovo il file {service_script}")
        return

    # 2. Trova l'eseguibile Python (usa pythonw per nascondere la console)
    python_exe = sys.executable
    # Se siamo su Windows, cerchiamo pythonw.exe nella stessa cartella di python.exe
    if sys.platform == 'win32' and "python.exe" in python_exe:
        candidate = python_exe.replace("python.exe", "pythonw.exe")
        if os.path.exists(candidate):
            python_exe = candidate
    
    # 3. Definisci il comando da eseguire
    # Usa le virgolette per gestire spazi nei percorsi
    task_command = f'"{python_exe}" "{service_script}"'
    task_name = "AutomationTaskScheduler_Service"
    
    print("-" * 50)
    print(f"Configurazione Task Windows: {task_name}")
    print(f"Target Script: {service_script}")
    print(f"Trigger: All\'accesso dell\'utente (ONLOGON)")
    print("-" * 50)

    # 4. Costruisci il comando schtasks
    # /Create: Crea nuovo task
    # /SC ONLOGON: Trigger al login
    # /TN: Nome del task
    # /TR: Comando da eseguire (Task Run)
    # /F: Forza sovrascrittura se esiste
    cmd = [
        "schtasks", "/Create",
        "/SC", "ONLOGON",
        "/TN", task_name,
        "/TR", task_command,
        "/F"
    ]

    # Esegui il comando
    try:
        # Nota: Su Windows 10/11 potrebbe richiedere privilegi amministrativi per alcuni trigger,
        # ma ONLOGON per l\'utente corrente di solito funziona.
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("\n✅ SUCCESSO!")
        print(f"Il task '{task_name}' è stato creato correttamente.")
        print("Il servizio si avvierà automaticamente al prossimo login di Windows.")
        print("\nPuoi verificarlo aprendo 'Utilità di pianificazione' (Task Scheduler).")
    except subprocess.CalledProcessError as e:
        print("\n❌ ERRORE durante la creazione del task.")
        print(f"Codice uscita: {e.returncode}")
        print("Dettagli errore:")
        print(e.stderr)
        print("-" * 30)
        print("SUGGERIMENTO: Prova ad eseguire questo script come Amministratore.")
        print("Apri un terminale (cmd/powershell) come Amministratore ed esegui:")
        print(f'python "{current_script}"')

if __name__ == "__main__":
    install_task()
