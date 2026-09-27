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
function Test-ServiceIdentity($service) {
    try {
        if ($service.Name -eq 'backend') {
            $document = Invoke-RestMethod -Uri "http://127.0.0.1:$($service.Port)/openapi.json" -TimeoutSec 2
            return $document.info.title -eq 'UrbanIQ API'
        }
        $page = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$($service.Port)/" -TimeoutSec 2
        $expectedTitle = [regex]::Escape("$($service.Name)-portal")
        return $page.Content -match "<title>\s*$expectedTitle\s*</title>"
    } catch {
        return $false
    }
}
function Test-PortalImports($service) {
    if ($service.Name -eq 'backend') { return }
    & $node (Join-Path $root 'scripts/check_portal_imports.mjs') --port $service.Port
    if ($LASTEXITCODE -ne 0) {
        throw "$($service.Name) is responding, but its page imports failed. Check .runtime/$($service.Name).error.log."
    }
}
foreach ($service in $services) {
    $client = New-Object System.Net.Sockets.TcpClient
    try { $client.Connect('127.0.0.1', $service.Port); $occupied = $true } catch { $occupied = $false } finally { $client.Dispose() }
    if ($occupied) {
        if (-not (Test-ServiceIdentity $service)) {
            throw "Port $($service.Port) is occupied, but it is not serving $($service.Name). Check the existing process before restarting this launcher."
        }
        Test-PortalImports $service
        Write-Host "$($service.Name) verified: http://127.0.0.1:$($service.Port)"
        continue
    }
    $process = Start-Process -FilePath $service.Exe -ArgumentList $service.Args -WorkingDirectory (Join-Path $root $service.Dir) -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs "$($service.Name).log") -RedirectStandardError (Join-Path $logs "$($service.Name).error.log") -PassThru
    $process.Id | Set-Content (Join-Path $logs "$($service.Name).pid")
    $ready = $false
    $deadline = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $deadline) {
        if ($process.HasExited) { break }
        if (Test-ServiceIdentity $service) { $ready = $true; break }
        Start-Sleep -Milliseconds 250
    }
    if (-not $ready) { throw "$($service.Name) did not start correctly. Check .runtime/$($service.Name).error.log." }
    Test-PortalImports $service
    Write-Host "$($service.Name) verified: http://127.0.0.1:$($service.Port) (PID $($process.Id))"
}
