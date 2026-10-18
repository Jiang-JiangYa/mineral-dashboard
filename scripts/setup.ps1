$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = 'utf-8'
if (-not (Test-Path '.venv/Scripts/python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw '请先安装 Python 3.11 或以上版本（建议 3.12，64 位）' }
}
& .venv/Scripts/python.exe -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Python 依赖安装失败，请检查网络' }
npm ci
if ($LASTEXITCODE -ne 0) { throw 'npm 依赖安装失败' }
if (-not (Test-Path '.env')) { Copy-Item '.env.example' '.env' }
& .venv/Scripts/python.exe -m pipeline bootstrap
if ($LASTEXITCODE -ne 0) { throw '数据库初始化失败' }
& .venv/Scripts/python.exe -m eval.run
if ($LASTEXITCODE -ne 0) { throw '评估失败' }
npm run build
if ($LASTEXITCODE -ne 0) { throw '前端构建失败' }
Write-Host '初始化完成。运行 npm start，打开 http://127.0.0.1:8000'
