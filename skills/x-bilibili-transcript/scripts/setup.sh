#!/usr/bin/env bash
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then
    brew install uv
  else
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
  fi
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  if ! command -v brew >/dev/null 2>&1; then
    printf '需要通过 Homebrew 自动安装音视频组件。\n' >&2
    exit 1
  fi
  brew install ffmpeg
fi

if ! command -v yt-dlp >/dev/null 2>&1; then
  uv tool install --python 3.12 yt-dlp
fi

if ! command -v mlx_whisper >/dev/null 2>&1; then
  uv tool install --python 3.12 mlx-whisper
fi

printf 'X / B 站转写环境已准备好。\n'
