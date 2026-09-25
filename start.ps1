$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$pythonPath = Join-Path $root '.venv/Scripts/python.exe'
if (-not (Test-Path $pythonPath)) { $pythonPath = Join-Path $root '../.venv/Scripts/python.exe' }
if (-not (Test-Path $pythonPath)) { throw 'Run python scripts/setup.py first.' }
$python = (Resolve-Path $pythonPath).Path
if (-not (Test-Path (Join-Path $root 'backend/.env'))) { throw 'Run python scripts/setup.py to create backend/.env.' }
$node = (Get-Command node).Source
$logs = Join-Path $root '.runtime'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$services = @(
    @{Name='backend'; Dir='backend'; Exe=$python; Args=@('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000'); Port=8000},
    @{Name='user'; Dir='user_portal'; Exe=$node; Args=@('node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5173','--strictPort'); Port=5173},
    @{Name='government'; Dir='government_portal'; Exe=$node; Args=@('node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5174','--strictPort'); Port=5174}
)
foreach ($service in $services) {
    $client = New-Object System.Net.Sockets.TcpClient
    try { $client.Connect('127.0.0.1', $service.Port); $occupied = $true } catch { $occupied = $false } finally { $client.Dispose() }
    if ($occupied) { Write-Host "Port $($service.Port) already occupied; leaving existing process running."; continue }
    $process = Start-Process -FilePath $service.Exe -ArgumentList $service.Args -WorkingDirectory (Join-Path $root $service.Dir) -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs "$($service.Name).log") -RedirectStandardError (Join-Path $logs "$($service.Name).error.log") -PassThru
    $process.Id | Set-Content (Join-Path $logs "$($service.Name).pid")
    Write-Host "$($service.Name): http://127.0.0.1:$($service.Port) (PID $($process.Id))"
}
