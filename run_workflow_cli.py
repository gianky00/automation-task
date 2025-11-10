import sys
import argparse
from core_logic import setup_logging, execute_flow

def main():
    """
    Punto di ingresso per l'esecuzione di un flusso di lavoro da riga di comando.
    Questo script viene chiamato dalla GUI per eseguire un flusso in una nuova finestra.
    """
    parser = argparse.ArgumentParser(description="Esegue un flusso di lavoro specifico.")
    parser.add_argument("flow_name", help="Il nome del flusso di lavoro da eseguire.")
    parser.add_argument("tasks", nargs='+', help="Elenco dei percorsi degli script da eseguire in sequenza.")

    args = parser.parse_args()

    # Configura il logging in modo che appaia su questa console
    setup_logging()

    # Esegui il flusso
    execute_flow(args.flow_name, args.tasks)

    # Mantieni la finestra aperta per permettere all'utente di leggere i log
    print("\n--- ESECUZIONE COMPLETATA ---")
    input("Premere Invio per chiudere questa finestra...")

if __name__ == "__main__":
    main()
