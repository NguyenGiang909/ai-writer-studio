#requires -Version 5.1
<#
.SYNOPSIS
  Build ban dong goi desktop AI Writer Studio (Windows).

.DESCRIPTION
  1. Frontend: next build (output: standalone) voi NEXT_PUBLIC_API_URL
     bake san -> copy .next/standalone/* -> package/web/
               copy .next/static      -> package/web/.next/static
               copy public            -> package/web/public
  2. Backend:  pyinstaller writer-api.spec -> package/writer-api.exe
  3. Stamp:    build_id.txt = git rev + timestamp -> /health tra ve
  4. Verify:   chay server.js tren port tam, curl trang chu phai 200

  Chay:  powershell -ExecutionPolicy Bypass -File package\build_package.ps1
  Yeu cau: node + npm tren PATH; .venv backend co pyinstaller.
#>
$ErrorActionPreference = 'Stop'
$ROOT   = Split-Path -Parent $PSScriptRoot            # repo root
$PKG    = $PSScriptRoot                                # package/
$WEB    = Join-Path $PKG 'web'
$FE     = Join-Path $ROOT 'frontend'
$BE     = Join-Path $ROOT 'backend'
$PY     = Join-Path $BE '.venv\Scripts\python.exe'
$API_URL = 'http://127.0.0.1:8765'

Write-Host '== AI Writer Studio build =='

# ---------- 0. preflight ----------
foreach ($p in @($FE, $BE, $PY)) {
    if (-not (Test-Path $p)) { throw "Thieu: $p" }
}
if (-not (Test-Path (Join-Path $PKG 'node.exe'))) {
    throw 'Thieu package/node.exe - copy node.exe (x64) vao package/ truoc.'
}

# ---------- 1. frontend ----------
Write-Host '[1/5] Frontend build (standalone)...'
Push-Location $FE
$env:NEXT_PUBLIC_API_URL = $API_URL
npm run build
if ($LASTEXITCODE -ne 0) { throw 'next build failed' }
Pop-Location

$SA = Join-Path $FE '.next\standalone'
if (-not (Test-Path (Join-Path $SA 'server.js'))) {
    throw "Khong thay .next/standalone/server.js - next.config output: 'standalone'?"
}

Write-Host '      copy standalone -> package/web/'
if (Test-Path $WEB) { Remove-Item $WEB -Recurse -Force }
New-Item -ItemType Directory -Path $WEB | Out-Null
Copy-Item "$SA\*" $WEB -Recurse -Force
# static + public phai copy TAY (standalone khong chua)
New-Item -ItemType Directory -Path (Join-Path $WEB '.next') -Force | Out-Null
Copy-Item (Join-Path $FE '.next\static') (Join-Path $WEB '.next\static') -Recurse -Force
if (Test-Path (Join-Path $FE 'public')) {
    Copy-Item (Join-Path $FE 'public') (Join-Path $WEB 'public') -Recurse -Force
}

# ---------- 2. backend ----------
Write-Host '[2/5] PyInstaller writer-api.exe...'
Push-Location $BE
& $PY -m PyInstaller writer-api.spec --noconfirm --distpath (Join-Path $BE 'dist') `
    --workpath (Join-Path $BE 'build')
if ($LASTEXITCODE -ne 0) { throw 'pyinstaller failed' }
Pop-Location
Copy-Item (Join-Path $BE 'dist\writer-api.exe') (Join-Path $PKG 'writer-api.exe') -Force

# ---------- 3. stamp ----------
Write-Host '[3/5] build_id.txt...'
$rev = 'nogit'
try { $rev = (git -C $ROOT rev-parse --short HEAD) } catch {}
$stamp = '{0}-{1}' -f $rev, (Get-Date -Format 'yyyyMMdd-HHmm')
Set-Content -Path (Join-Path $PKG 'build_id.txt') -Value $stamp -NoNewline
Write-Host "      build_id = $stamp"

# ---------- 4. verify ----------
Write-Host '[4/5] Smoke test web...'
$env:PORT = '3399'; $env:HOSTNAME = '127.0.0.1'
$job = Start-Process -FilePath (Join-Path $PKG 'node.exe') `
    -ArgumentList 'web\server.js' -WorkingDirectory $PKG `
    -PassThru -WindowStyle Hidden `
    -RedirectStandardError (Join-Path $env:TEMP 'pkg-web-err.log')
$ok = $false
foreach ($i in 1..20) {
    Start-Sleep -Milliseconds 800
    try {
        $r = Invoke-WebRequest 'http://127.0.0.1:3399' -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch {}
}
Stop-Process -Id $job.Id -Force -ErrorAction SilentlyContinue
if (-not $ok) {
    Write-Warning 'server.js khong phuc vu duoc - kiem tra copy standalone.'
} else {
    Write-Host '      web OK (200)'
}

Write-Host '[5/5] Xong.'
Write-Host "Go bo tai: $PKG  (start.bat / stop.bat)"
