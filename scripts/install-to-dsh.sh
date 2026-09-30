#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEST_BASE="$HOME/.dsh/skills"
SKILL_ONE="xiaohongshu-creator-archive"
SKILL_TWO="x-bilibili-transcript"
SKILL_THREE="multi-platform-media-transcript"
SKILL_FOUR="podcast-to-feishu"

usage() {
  cat <<'EOF'
用法：
  bash scripts/install-to-dsh.sh <skill-name>
  bash scripts/install-to-dsh.sh --all
  bash scripts/install-to-dsh.sh --skip-setup <skill-name>

可选 Skill：
  xiaohongshu-creator-archive
  x-bilibili-transcript
  multi-platform-media-transcript
  podcast-to-feishu
EOF
}

SKIP_SETUP="0"
if [ "$#" -gt 0 ] && [ "$1" = "--skip-setup" ]; then
  SKIP_SETUP="1"
  shift
fi

install_one() {
  local skill_name="$1"
  local source_dir="$ROOT_DIR/skills/$skill_name"
  local target_dir="$DEST_BASE/$skill_name"

  if [ ! -f "$source_dir/SKILL.md" ]; then
    printf '没有找到 Skill：%s\n' "$skill_name" >&2
    exit 1
  fi

  if [ "$SKIP_SETUP" != "1" ] && [ -f "$source_dir/scripts/setup.sh" ]; then
    bash "$source_dir/scripts/setup.sh"
  fi

  mkdir -p "$DEST_BASE"
  if [ -e "$target_dir" ]; then
    local backup_dir="$target_dir.backup.$(date +%Y%m%d%H%M%S)"
    mv "$target_dir" "$backup_dir"
    printf '已有版本已备份到：%s\n' "$backup_dir"
  fi

  cp -R "$source_dir" "$target_dir"
  printf '已安装：%s\n' "$skill_name"
}

if [ "$#" -ne 1 ]; then
  usage
  exit 2
fi

if [ "$1" = "--all" ]; then
  install_one "$SKILL_ONE"
  install_one "$SKILL_TWO"
  install_one "$SKILL_THREE"
  install_one "$SKILL_FOUR"
  printf '四个 Skill 已安装到 %s\n' "$DEST_BASE"
  exit 0
fi

case "$1" in
  "$SKILL_ONE"|"$SKILL_TWO"|"$SKILL_THREE"|"$SKILL_FOUR")
    install_one "$1"
    ;;
  *)
    usage
    exit 2
    ;;
esac
