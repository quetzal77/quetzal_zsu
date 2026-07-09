param(
    [Parameter(Position = 0)]
    [ValidateSet("run", "check", "install", "stop")]
    [string]$Command = "run",

    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000,
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot
$PidFile = Join-Path $ProjectRoot ".quetzal_zsu.pid"

function Write-Step($msg) {
    Write-Host "==> $msg" -ForegroundColor Cyan
}

function Get-PythonCommand {
    foreach ($candidate in @("python", "py")) {
        $found = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($found) { return $candidate }
    }
    Write-Host "Python не знайдено в PATH. Встанови Python 3.12+ і повтори." -ForegroundColor Red
    exit 1
}

function Test-Dependencies($Python) {
    $checkScript = "import importlib.util as u, sys; mods=['fastapi','uvicorn','jinja2','multipart']; missing=[m for m in mods if u.find_spec(m) is None]; sys.exit(1 if missing else 0)"
    & $Python -c $checkScript
    return ($LASTEXITCODE -eq 0)
}

function Install-Dependencies($Python) {
    Write-Step "Встановлюю залежності з requirements.txt..."
    & $Python -m pip install -q -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Не вдалося встановити залежності." -ForegroundColor Red
        exit 1
    }
}

function Test-Database {
    $dbPath = Join-Path $ProjectRoot "data\quetzal_zsu.db"
    if (-not (Test-Path $dbPath)) {
        Write-Host "Не знайдено data\quetzal_zsu.db. Проєкт не запускати без бази даних." -ForegroundColor Red
        exit 1
    }
    Write-Step "База даних знайдена: $dbPath"
}

# --- stop не потребує Python/залежностей/БД, лише зупиняє процес ---
if ($Command -eq "stop") {
    if (-not (Test-Path $PidFile)) {
        Write-Host "Сервер не запущено (немає .quetzal_zsu.pid)." -ForegroundColor Yellow
        exit 0
    }
    $savedPid = Get-Content -Path $PidFile -Raw | ForEach-Object { $_.Trim() }
    $proc = Get-Process -Id $savedPid -ErrorAction SilentlyContinue
    if (-not $proc) {
        Write-Host "Процес (PID $savedPid) вже не працює. Прибираю pid-файл." -ForegroundColor Yellow
        Remove-Item $PidFile -ErrorAction SilentlyContinue
        exit 0
    }
    # uvicorn --reload запускає дочірній процес-воркер, який і слухає порт;
    # звичайний Stop-Process вбиває лише батьківський watcher і лишає сирітський
    # процес на порту. /T вбиває все дерево процесів.
    taskkill /PID $savedPid /T /F | Out-Null
    Remove-Item $PidFile -ErrorAction SilentlyContinue
    Write-Step "Сервер (PID $savedPid) і його дочірні процеси зупинено."
    exit 0
}

$Python = Get-PythonCommand
Write-Step "Python: $Python ($(& $Python --version))"

Write-Step "Перевіряю залежності..."
if (-not (Test-Dependencies $Python)) {
    Write-Host "Деякі пакети відсутні." -ForegroundColor Yellow
    Install-Dependencies $Python
} else {
    Write-Step "Усі залежності вже встановлені."
}

Test-Database

if ($Command -eq "check") {
    Write-Step "Усе на місці. Готово до запуску: quetzal_zsu run"
    exit 0
}

if ($Command -eq "install") {
    Install-Dependencies $Python
    Write-Step "Залежності встановлено."
    exit 0
}

if (Test-Path $PidFile) {
    $existingPid = Get-Content -Path $PidFile -Raw | ForEach-Object { $_.Trim() }
    if (Get-Process -Id $existingPid -ErrorAction SilentlyContinue) {
        Write-Host "Сервер уже запущено (PID $existingPid). Спочатку виконай: quetzal_zsu stop" -ForegroundColor Yellow
        exit 1
    }
    Remove-Item $PidFile -ErrorAction SilentlyContinue
}

$uvicornArgs = @("-m", "uvicorn", "app.main:app", "--host", $BindHost, "--port", $Port)
if (-not $NoReload) { $uvicornArgs += "--reload" }

Write-Step "Запускаю сервер на http://${BindHost}:${Port} (Ctrl+C або 'quetzal_zsu stop' в іншому терміналі, щоб зупинити) ..."

$proc = Start-Process -FilePath $Python -ArgumentList $uvicornArgs -NoNewWindow -PassThru
$proc.Id | Set-Content -Path $PidFile

try {
    Wait-Process -Id $proc.Id
} finally {
    # Ctrl+C сюди теж потрапляє через finally — прибираємо дочірні процеси
    # (воркер --reload), інакше вони лишаються висіти на порту.
    taskkill /PID $proc.Id /T /F 2>$null | Out-Null
    Remove-Item $PidFile -ErrorAction SilentlyContinue
}
