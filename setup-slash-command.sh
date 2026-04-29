#!/usr/bin/env bash
#
# setup-slash-command.sh — Installs /audit-mcp slash command for Claude Code
#
# Usage:
#   ./setup-slash-command.sh
#
# What it does:
#   1. Locates this script's directory (the skill repo root)
#   2. Creates ~/.claude/commands/ if missing
#   3. Symlinks .claude/commands/audit-mcp.md to ~/.claude/commands/audit-mcp.md
#   4. Sets MCP_AUDIT_SKILL_PATH hint in shell rc file (optional)
#
# After running this, /audit-mcp <repo-url> works in any Claude Code session.

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$SKILL_DIR/.claude/commands/audit-mcp.md"
TARGET_DIR="$HOME/.claude/commands"
TARGET="$TARGET_DIR/audit-mcp.md"

if [[ ! -f "$SOURCE" ]]; then
  echo "Error: $SOURCE not found. Are you running this from the skill repo root?" >&2
  exit 1
fi

mkdir -p "$TARGET_DIR"

if [[ -L "$TARGET" ]]; then
  current_target=$(readlink "$TARGET")
  if [[ "$current_target" == "$SOURCE" ]]; then
    echo "Already linked: $TARGET -> $SOURCE"
  else
    echo "Existing symlink points elsewhere ($current_target). Replacing."
    ln -sf "$SOURCE" "$TARGET"
  fi
elif [[ -f "$TARGET" ]]; then
  echo "Warning: $TARGET exists as a regular file (not a symlink)."
  read -p "Backup to $TARGET.bak and replace with symlink? [y/N] " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    mv "$TARGET" "$TARGET.bak"
    ln -s "$SOURCE" "$TARGET"
    echo "Old file backed up to $TARGET.bak"
  else
    echo "Aborted. No changes made."
    exit 1
  fi
else
  ln -s "$SOURCE" "$TARGET"
  echo "Linked: $TARGET -> $SOURCE"
fi

echo
echo "✓ /audit-mcp slash command is now globally available in Claude Code."
echo
echo "Optional: add MCP_AUDIT_SKILL_PATH to your shell rc to skip path-prompts:"
echo "  echo 'export MCP_AUDIT_SKILL_PATH=\"$SKILL_DIR\"' >> ~/.bashrc"
echo "  # or for zsh:"
echo "  echo 'export MCP_AUDIT_SKILL_PATH=\"$SKILL_DIR\"' >> ~/.zshrc"
echo
echo "Usage:"
echo "  cd <any-mcp-server-repo>"
echo "  claude"
echo "  > /audit-mcp ."
echo "  > /audit-mcp https://github.com/malkreide/zh-education-mcp"
