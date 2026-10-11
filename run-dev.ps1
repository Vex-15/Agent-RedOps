$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

$backend = Start-Job -Name "backend" -ArgumentList (Join-Path $repoRoot "backend") -ScriptBlock {
    param($workingDirectory)
    Set-Location $workingDirectory
    uvicorn main:app --reload --port 8000
}

$frontend = Start-Job -Name "frontend" -ArgumentList (Join-Path $repoRoot "frontend") -ScriptBlock {
    param($workingDirectory)
    Set-Location $workingDirectory
    npm run dev
}

Write-Host "Backend:  http://127.0.0.1:8000"
Write-Host "Frontend: http://127.0.0.1:5173"
Write-Host "Press Ctrl+C to stop both."

try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
}
finally {
    Stop-Job -Job $backend, $frontend -ErrorAction SilentlyContinue
    Remove-Job -Job $backend, $frontend -Force -ErrorAction SilentlyContinue
}
