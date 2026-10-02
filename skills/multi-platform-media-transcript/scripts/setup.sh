#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SYSTEM="$(uname -s)"
ARCH="$(uname -m)"
CACHE_ROOT="${XDG_CACHE_HOME:-$HOME/.cache}/link2content"
VENV_DIR="$CACHE_ROOT/venv"

say() { printf '\n[Link2Content] %s\n' "$*"; }
fail() { printf '\n[Link2Content] 安装未完成：%s\n' "$*" >&2; exit 1; }
run_privileged() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    fail "安装系统级 ffmpeg 需要管理员权限。请使用管理员终端后重试。"
  fi
}

if ! command -v ffmpeg >/dev/null 2>&1; then
  if [ "$SYSTEM" = "Darwin" ]; then
    if ! command -v brew >/dev/null 2>&1; then
      say "未检测到 Homebrew，正在运行官方安装程序（可能需要确认开发者工具安装或输入系统密码）。"
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
      if [ -x /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
      elif [ -x /usr/local/bin/brew ]; then
        eval "$(/usr/local/bin/brew shellenv)"
      fi
    fi
    command -v brew >/dev/null 2>&1 || fail "Homebrew 安装后仍不可用，请重新打开终端再运行本 Skill。"
    brew install ffmpeg
  elif [ "$SYSTEM" = "Linux" ]; then
    if command -v apt-get >/dev/null 2>&1; then
      run_privileged apt-get update
      run_privileged apt-get install -y ffmpeg
    elif command -v dnf >/dev/null 2>&1; then
      run_privileged dnf install -y ffmpeg
    elif command -v pacman >/dev/null 2>&1; then
      run_privileged pacman -S --needed --noconfirm ffmpeg
    else
      fail "当前 Linux 发行版没有受支持的自动包管理器（apt、dnf 或 pacman）；请先安装 ffmpeg，再重试。"
    fi
  else
    fail "请在 Windows 使用 scripts/setup.ps1 安装 FFmpeg 和本地环境。"
  fi
fi

if ! command -v uv >/dev/null 2>&1; then
  say "正在安装 Python 环境管理器 uv。"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi
command -v uv >/dev/null 2>&1 || fail "uv 未安装成功。"
command -v ffmpeg >/dev/null 2>&1 || fail "ffmpeg 未安装成功；请重新打开终端后运行 scripts/setup.sh。"

mkdir -p "$CACHE_ROOT"
uv python install 3.12
if [ ! -x "$VENV_DIR/bin/python" ]; then
  uv venv --python 3.12 "$VENV_DIR"
fi
PYTHON="$VENV_DIR/bin/python"

say "正在安装 Link2Content 的本地媒体、OCR 和网页解析组件。"
uv pip install --python "$PYTHON" yt-dlp crawl4ai 'rapidocr>=3.7.0' onnxruntime huggingface_hub hf_xet

if [ "$SYSTEM" = "Darwin" ] && [ "$ARCH" = "arm64" ]; then
  say "检测到 Apple 芯片：安装 MLX Whisper。"
  uv pip install --python "$PYTHON" mlx-whisper
else
  say "安装 faster-whisper 本地转写后端。"
  uv pip install --python "$PYTHON" faster-whisper
fi

if [ -x "$VENV_DIR/bin/crawl4ai-setup" ]; then
  say "正在准备网页解析所需的本地浏览器。"
  "$VENV_DIR/bin/crawl4ai-setup"
fi

say "正在预下载语音转写和中文 OCR 模型。首次安装会下载约 1.6 GB 的 Whisper 模型。"
"$PYTHON" "$SKILL_DIR/scripts/prepare_models.py"
if [ -x "$VENV_DIR/bin/rapidocr" ]; then
  "$VENV_DIR/bin/rapidocr" download_models
fi

say "安装完成。Skill 环境：$VENV_DIR"
say "本地模型已缓存；把链接发给 Agent 即可开始整理。"
