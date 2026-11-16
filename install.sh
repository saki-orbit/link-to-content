#!/usr/bin/env bash
# One-command install: fetch this repository, prepare the local environment, install the skill.
#
#   curl -fsSL https://raw.githubusercontent.com/saki-orbit/link-to-content/main/install.sh | bash
#
# 可选环境变量：
#   L2C_HOME   仓库/安装目录，默认 ~/.local/share/link2content
#   L2C_REPO   仓库地址，默认官方 GitHub 仓库
set -euo pipefail

REPO_URL="${L2C_REPO:-https://github.com/saki-orbit/link-to-content.git}"
DEST="${L2C_HOME:-$HOME/.local/share/link2content}"

say() { printf '[l2c] %s\n' "$*"; }
die() { printf '[l2c] %s\n' "$*" >&2; exit 1; }

command -v git >/dev/null 2>&1 || die "需要 git，请先安装后重试。"

if [ -d "$DEST/.git" ]; then
  say "更新已有安装：$DEST"
  git -C "$DEST" pull --ff-only
else
  say "下载到：$DEST"
  mkdir -p "$(dirname "$DEST")"
  git clone --depth 1 "$REPO_URL" "$DEST"
fi

# 允许显式写 install：curl … | bash -s -- install --target agents
if [ "${1:-}" = "install" ]; then
  shift
fi

exec bash "$DEST/bin/l2c" install "$@"
