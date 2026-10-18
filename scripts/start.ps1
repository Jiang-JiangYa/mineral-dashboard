$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$env:PYTHONIOENCODING = 'utf-8'
if (-not (Test-Path '.venv/Scripts/python.exe')) { throw '请先执行 npm run setup' }
npm run build
if ($LASTEXITCODE -ne 0) { throw '前端构建失败' }
Write-Host '网页：http://127.0.0.1:8000   API 文档：http://127.0.0.1:8000/docs'
& .venv/Scripts/python.exe -m uvicorn serve.app:app --host 127.0.0.1 --port 8000
