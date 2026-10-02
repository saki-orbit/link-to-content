$ErrorActionPreference = 'Stop'

$CacheRoot = Join-Path $env:LOCALAPPDATA 'Link2Content'
$VenvDir = Join-Path $CacheRoot 'venv'
$Python = Join-Path $VenvDir 'Scripts\python.exe'

function Write-Step([string]$Message) {
    Write-Host "`n[Link2Content] $Message"
}

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw '当前 Windows 没有 winget。请先安装“应用安装程序”（App Installer），然后重新运行本脚本。'
}

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Step '正在安装 FFmpeg。'
    winget install --id Gyan.FFmpeg --exact --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw 'FFmpeg 安装失败。' }
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    throw 'FFmpeg 已提交安装，但当前终端还找不到它。请重新打开 Agent/终端后再运行本脚本。'
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Step '正在安装 Python 环境管理器 uv。'
    powershell -ExecutionPolicy ByPass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    if ($LASTEXITCODE -ne 0) { throw 'uv 安装失败。' }
    $env:Path += ";$env:USERPROFILE\.local\bin;$env:USERPROFILE\.cargo\bin"
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv 未安装成功。'
}

New-Item -ItemType Directory -Force -Path $CacheRoot | Out-Null
uv python install 3.12
if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 安装失败。' }
if (-not (Test-Path $Python)) {
    uv venv --python 3.12 $VenvDir
    if ($LASTEXITCODE -ne 0) { throw 'Link2Content Python 环境创建失败。' }
}

Write-Step '正在安装 Link2Content 的本地媒体、OCR 和网页解析组件。'
uv pip install --python $Python yt-dlp crawl4ai 'rapidocr>=3.7.0' onnxruntime huggingface_hub hf_xet faster-whisper
if ($LASTEXITCODE -ne 0) { throw '本地依赖安装失败。' }

$CrawlSetup = Join-Path $VenvDir 'Scripts\crawl4ai-setup.exe'
if (Test-Path $CrawlSetup) {
    Write-Step '正在准备网页解析所需的本地浏览器。'
    & $CrawlSetup
    if ($LASTEXITCODE -ne 0) { throw '网页解析浏览器安装失败。' }
}

Write-Step '正在预下载语音转写和中文 OCR 模型。首次安装会下载约 1.6 GB 的 Whisper 模型。'
& $Python (Join-Path $PSScriptRoot 'prepare_models.py')
if ($LASTEXITCODE -ne 0) { throw 'Whisper 模型预下载失败。' }
$RapidOcr = Join-Path $VenvDir 'Scripts\rapidocr.exe'
if (Test-Path $RapidOcr) {
    & $RapidOcr download_models
    if ($LASTEXITCODE -ne 0) { throw 'RapidOCR 模型下载失败。' }
}

Write-Step "安装完成。Skill 环境：$VenvDir"
Write-Step '本地模型已缓存；把链接发给 Agent 即可开始整理。'
