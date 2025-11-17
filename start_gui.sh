#!/bin/bash
# Avvia l'interfaccia grafica del configuratore di flussi.
# L'output viene reindirizzato su un file di log per il debug.
python gui_configurator.py > gui.log 2>&1 &
