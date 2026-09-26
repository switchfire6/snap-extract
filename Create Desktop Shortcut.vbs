Option Explicit
Dim shell, files, folder, target, linkPath, shortcut
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
folder = files.GetParentFolderName(WScript.ScriptFullName)
target = folder & "\Snap Extract.exe"
If Not files.FileExists(target) Then target = folder & "\dist\Snap Extract\Snap Extract.exe"
If Not files.FileExists(target) Then target = folder & "\Start Snap Extract.cmd"
If Not files.FileExists(target) Then
    MsgBox "Extract the complete Snap Extract download before creating a shortcut.", vbExclamation, "Snap Extract"
    WScript.Quit 1
End If
linkPath = shell.SpecialFolders("Desktop") & "\Snap Extract.lnk"
On Error Resume Next
Set shortcut = shell.CreateShortcut(linkPath)
shortcut.TargetPath = target
shortcut.WorkingDirectory = folder
shortcut.Description = "Open Snap Extract to export your collection and saved decks."
If LCase(files.GetExtensionName(target)) = "exe" Then shortcut.IconLocation = target & ",0"
shortcut.Save
If Err.Number <> 0 Then
    MsgBox "Could not create the desktop shortcut: " & Err.Description, vbExclamation, "Snap Extract"
    WScript.Quit 1
End If
On Error GoTo 0
MsgBox "Snap Extract is now on your desktop. Keep this app folder in place so the shortcut keeps working.", vbInformation, "Snap Extract"
