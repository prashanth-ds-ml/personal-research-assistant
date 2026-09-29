<#
Starts the personal research assistant's backend (langgraph dev) and
dashboard (Next.js) in the background, non-blocking. Meant to be run at
logon via register-task.ps1's scheduled task, but safe to run manually too.
#>

# Portable: derives everything from this script's own location, so it works
# regardless of where the repo is cloned to.
$projectRoot   = Split-Path -Parent $PSScriptRoot
$venvScripts   = "$projectRoot\.venv\Scripts"
$dashboardRoot = "$projectRoot\dashboard"
$logsDir       = "$projectRoot\logs"
$dashboardLogsDir = "$dashboardRoot\logs"

New-Item -ItemType Directory -Force $logsDir | Out-Null
New-Item -ItemType Directory -Force $dashboardLogsDir | Out-Null

# Fail fast (and visibly, in the log) if Ollama isn't up yet, rather than
# letting the first research run die deep inside generate_query.
try {
    Invoke-WebRequest -Uri "http://localhost:11434/api/version" -TimeoutSec 3 -UseBasicParsing | Out-Null
} catch {
    Add-Content "$logsDir\startup.log" "$(Get-Date -Format o) WARNING: Ollama not reachable at http://localhost:11434 - start it before researching."
}

# cwd matters: langgraph.json's "env": "./.env" and "dependencies": ["."]
# are relative to it, and port 2024 is avoided on this machine (see the
# plan's "ports 2024/3000 are poisoned" note) - always use 2025.
Start-Process -FilePath "$venvScripts\langgraph.exe" -ArgumentList "dev", "--no-browser", "--no-reload", "--port", "2025" `
    -WorkingDirectory $projectRoot -WindowStyle Hidden `
    -RedirectStandardOutput "$logsDir\langgraph-dev.log" `
    -RedirectStandardError  "$logsDir\langgraph-dev.err.log"

# The dashboard's own package.json start script already binds port 3001.
Start-Process -FilePath "npm.cmd" -ArgumentList "run", "start" `
    -WorkingDirectory $dashboardRoot -WindowStyle Hidden `
    -RedirectStandardOutput "$dashboardLogsDir\nextjs.log" `
    -RedirectStandardError  "$dashboardLogsDir\nextjs.err.log"

Add-Content "$logsDir\startup.log" "$(Get-Date -Format o) Started langgraph dev (port 2025) and dashboard (port 3001)."
