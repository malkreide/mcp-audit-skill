#!/usr/bin/env bash
#
# setup-slash-command.sh — Installs /audit-mcp slash command and mcp-audit
# skill for Claude Code (CLI and Desktop).
#
# Usage:
#   ./setup-slash-command.sh
#
# What it does:
#   1. Locates this script's directory (the skill repo root)
#   2. Symlinks .claude/commands/audit-mcp.md to ~/.claude/commands/audit-mcp.md
#      (slash-command available globally in any Claude Code session)
#   3. Symlinks the repo root to ~/.claude/skills/mcp-audit/
#      (auto-loads as a Skill in Claude Code Desktop when description matches)
#   4. Sets MCP_AUDIT_SKILL_PATH hint in shell rc file (optional)
#
# After running this, both /audit-mcp <repo> (slash-command) and the
# mcp-audit skill (auto-activated by Claude Code) are available.

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# link_or_replace SOURCE TARGET — idempotent symlink with safe handling of
# pre-existing symlinks (matching or pointing elsewhere) and regular
# files/directories at the target path.
link_or_replace() {
  local source=$1
  local target=$2
  local target_dir
  target_dir="$(dirname "$target")"

  mkdir -p "$target_dir"

  if [[ -L "$target" ]]; then
    local current_target
    current_target=$(readlink "$target")
    if [[ "$current_target" == "$source" ]]; then
      echo "Already linked: $target -> $source"
      return 0
    fi
    echo "Existing symlink points elsewhere ($current_target). Replacing."
    ln -sfn "$source" "$target"
    return 0
  fi

  if [[ -e "$target" ]]; then
    echo "Warning: $target exists as a regular file/directory (not a symlink)."
    read -p "Backup to $target.bak and replace with symlink? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      mv "$target" "$target.bak"
      ln -sfn "$source" "$target"
      echo "Old file/directory backed up to $target.bak"
      return 0
    fi
    echo "Aborted for $target. No changes made."
    return 1
  fi

  ln -sfn "$source" "$target"
  echo "Linked: $target -> $source"
}

# 1. Slash-command: ~/.claude/commands/audit-mcp.md -> repo file
COMMAND_SOURCE="$SKILL_DIR/.claude/commands/audit-mcp.md"
COMMAND_TARGET="$HOME/.claude/commands/audit-mcp.md"

if [[ ! -f "$COMMAND_SOURCE" ]]; then
  echo "Error: $COMMAND_SOURCE not found. Are you running this from the skill repo root?" >&2
  exit 1
fi

link_or_replace "$COMMAND_SOURCE" "$COMMAND_TARGET" || true

# 2. Skill: ~/.claude/skills/mcp-audit -> repo root
SKILL_TARGET="$HOME/.claude/skills/mcp-audit"

if [[ ! -f "$SKILL_DIR/SKILL.md" ]]; then
  echo "Error: $SKILL_DIR/SKILL.md not found. Are you running this from the skill repo root?" >&2
  exit 1
fi

link_or_replace "$SKILL_DIR" "$SKILL_TARGET" || true

echo
echo "✓ /audit-mcp slash command and mcp-audit skill are now globally available in Claude Code."
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
echo
echo "Or let Claude auto-load the skill when you ask informally:"
echo "  > Audit den Server in diesem Repo gegen die Best Practices."
