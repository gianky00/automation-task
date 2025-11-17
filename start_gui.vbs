' Questo script avvia l'applicazione GUI Python senza mostrare una finestra di console.

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Ottiene il percorso completo della directory in cui si trova lo script VBS.
strScriptPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Costruisce il percorso completo per il file Python.
strPythonScript = objFSO.BuildPath(strScriptPath, "gui_configurator.py")

' Costruisce il comando per eseguire lo script con pythonw.exe, che è la versione
' "windowed" di Python (non mostra la console).
strCommand = "pythonw.exe """ & strPythonScript & """"

' Esegue il comando.
' Il primo parametro è il comando da eseguire.
' Il secondo (0) indica di nascondere la finestra.
' Il terzo (False) indica di non attendere il completamento del processo.
objShell.Run strCommand, 0, False
