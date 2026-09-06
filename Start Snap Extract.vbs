Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
folder = files.GetParentFolderName(WScript.ScriptFullName)
exe = folder & "\dist\Snap Extract.exe"
If files.FileExists(exe) Then
    shell.Run Chr(34) & exe & Chr(34), 1, False
Else
    shell.CurrentDirectory = folder
    shell.Run "pythonw.exe " & Chr(34) & folder & "\run_app.py" & Chr(34), 1, False
End If
