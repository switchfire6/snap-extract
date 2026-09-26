Option Explicit
Dim shell, files, folder, launcher, target
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
folder = files.GetParentFolderName(WScript.ScriptFullName)
target = folder & "\Snap Extract.exe"
If Not files.FileExists(target) Then target = folder & "\dist\Snap Extract\Snap Extract.exe"
If Not files.FileExists(target) Then target = folder & "\.venv\Scripts\pythonw.exe"
If files.FileExists(target) Then
    If LCase(files.GetFileName(target)) = "pythonw.exe" Then
        shell.Run Chr(34) & target & Chr(34) & " " & Chr(34) & folder & "\run_app.py" & Chr(34), 1, False
    Else
        shell.Run Chr(34) & target & Chr(34), 1, False
    End If
    WScript.Quit
End If
launcher = folder & "\Start Snap Extract.cmd"
If Not files.FileExists(launcher) Then
    MsgBox "Start Snap Extract.cmd is missing. Extract the complete download first.", vbExclamation, "Snap Extract"
    WScript.Quit 1
End If
' Show fallback diagnostics if no installed Python can be found.
shell.Run Chr(34) & launcher & Chr(34), 1, False
