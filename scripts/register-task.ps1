<#
Registers a Windows Task Scheduler task that runs start-research-assistant.ps1
at logon. Run this manually, once - it is NOT run automatically by anything
else in this project. Registering a scheduled task is a persistent,
system-level change, so this script is meant to be reviewed and run
deliberately, not invoked as a side effect of other setup.

Uses a plain "at logon, only when logged on" trigger (not "run whether user
is logged on or not") because the OS notification step (win11toast, a WinRT
toast) only works in the interactive user session.
#>

# Portable: derives the path from this script's own location.
$scriptPath = Join-Path $PSScriptRoot "start-research-assistant.ps1"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument `
    "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"

Register-ScheduledTask -TaskName "ResearchAssistantAutoStart" -Action $action -Trigger $trigger `
    -Description "Starts langgraph dev + the Next.js research dashboard at logon"

Write-Host "Registered task 'ResearchAssistantAutoStart'. It will run at your next logon."
Write-Host "To run it now without logging off: Start-ScheduledTask -TaskName ResearchAssistantAutoStart"
Write-Host "To remove it later: Unregister-ScheduledTask -TaskName ResearchAssistantAutoStart"
