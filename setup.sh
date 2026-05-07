#!/usr/bin/env bash
# vault-template setup script.
#
# Run this once after cloning vault-template into your Obsidian vault dir.
# It prompts for a few defaults, writes them into the scripts, and prints
# the snippets you need to paste into ~/.claude/ files.
#
# Idempotent: safe to re-run. Won't overwrite without asking.

set -euo pipefail

VAULT_ROOT="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS_DIR="$VAULT_ROOT/llmzone/shared/scripts"
SNIPPETS_DIR="$VAULT_ROOT/snippets"

bold() { printf "\033[1m%s\033[0m\n" "$1"; }
ok() { printf "  ✓ %s\n" "$1"; }
warn() { printf "  ⚠ %s\n" "$1"; }
skip() { printf "  - %s\n" "$1"; }

bold "vault-template setup"
echo "vault root: $VAULT_ROOT"
echo

# ------------------------------------------------------------ sanity checks

if ! command -v python3 >/dev/null 2>&1; then
    echo "✗ python3 not found on PATH. Install Python 3.10+ and re-run." >&2
    exit 1
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
ok "python3 $PY_VER"

if command -v gh >/dev/null 2>&1; then
    if gh auth status >/dev/null 2>&1; then
        ok "gh CLI installed and authenticated"
    else
        warn "gh CLI installed but not authenticated. Run \`gh auth login\` to enable PR auto-fill."
    fi
else
    warn "gh CLI not found. PR auto-fill (\`vault new pr\`) and \`vault prs\` will be unavailable until you install it."
fi

[[ -f "$SCRIPTS_DIR/_gh.py" ]] || { echo "✗ $SCRIPTS_DIR/_gh.py missing — is this the vault-template root?" >&2; exit 1; }

echo

# ------------------------------------------------------------ Q1: default GH repo

CURRENT_REPO=$(grep -E '^DEFAULT_REPO = ' "$SCRIPTS_DIR/_gh.py" | sed -E 's|.*"([^"]*)".*|\1|')
DISPLAY_CURRENT="${CURRENT_REPO:-(unset)}"
bold "GitHub default repo"
echo "Used as the fallback for \`vault new pr\`, \`vault prs\`, and \`--gh-sync\` when"
echo "no per-call --repo is given and a PR note's body has no GitHub URL."
echo "Format: owner/repo (e.g., octocat/hello-world). Leave empty to require --repo per call."
echo "Currently: $DISPLAY_CURRENT"
read -r -p "  New default repo [$CURRENT_REPO]: " GH_REPO
GH_REPO=${GH_REPO:-$CURRENT_REPO}

if [[ "$GH_REPO" != "$CURRENT_REPO" ]]; then
    sed -i.bak -E "s|^DEFAULT_REPO = .*|DEFAULT_REPO = \"$GH_REPO\"|" "$SCRIPTS_DIR/_gh.py"
    rm -f "$SCRIPTS_DIR/_gh.py.bak"
    if [[ -z "$GH_REPO" ]]; then
        ok "cleared DEFAULT_REPO (you'll need --repo OWNER/REPO on every gh-related call)"
    else
        ok "set DEFAULT_REPO=$GH_REPO in _gh.py"
    fi
else
    skip "DEFAULT_REPO unchanged"
fi
echo

# ------------------------------------------------------------ Q2: slash command

bold "/vault-checkin slash command"
echo "Installs ~/.claude/commands/vault-checkin.md so /vault-checkin works in Claude Code."
TARGET="$HOME/.claude/commands/vault-checkin.md"
if [[ -f "$TARGET" ]]; then
    read -r -p "  $TARGET already exists — overwrite? [y/N]: " ans
    if [[ "${ans:-N}" =~ ^[Yy]$ ]]; then
        DO_SLASH=1
    else
        DO_SLASH=0
    fi
else
    read -r -p "  Install /vault-checkin slash command? [Y/n]: " ans
    if [[ "${ans:-Y}" =~ ^[Yy]$ ]]; then
        DO_SLASH=1
    else
        DO_SLASH=0
    fi
fi
if [[ "$DO_SLASH" == "1" ]]; then
    mkdir -p "$HOME/.claude/commands"
    sed "s|<vault-root>|$VAULT_ROOT|g" "$SNIPPETS_DIR/vault-checkin.md" > "$TARGET"
    ok "installed $TARGET"
else
    skip "slash command not installed"
fi
echo

# ------------------------------------------------------------ Q3: smoke test

bold "Smoke test"
echo "Running \`vault rebuild\` to verify scripts work and indices initialize..."
if python3 "$SCRIPTS_DIR/vault.py" rebuild >/tmp/vault-setup-rebuild.log 2>&1; then
    ok "rebuild succeeded"
else
    echo "  ✗ rebuild failed. See /tmp/vault-setup-rebuild.log for details." >&2
    cat /tmp/vault-setup-rebuild.log >&2
    exit 1
fi
echo

# ------------------------------------------------------------ next steps

bold "Setup complete — manual steps remaining"
echo
echo "1. Add the vault context to your Claude Code instructions."
echo "   Append the following to ~/.claude/CLAUDE.md:"
echo "   ----------------------------------------------------------"
sed "s|<VAULT_PATH>|$VAULT_ROOT|g" "$SNIPPETS_DIR/CLAUDE.md.snippet" | sed 's/^/   /'
echo "   ----------------------------------------------------------"
echo
echo "2. Add a SessionEnd hook so indices auto-rebuild after every session."
echo "   Merge the following into ~/.claude/settings.json under the \"hooks\" key"
echo "   (don't replace existing hooks — merge into them):"
echo "   ----------------------------------------------------------"
sed "s|<VAULT_PATH>|$VAULT_ROOT|g" "$SNIPPETS_DIR/settings.json.snippet" | sed 's/^/   /'
echo "   ----------------------------------------------------------"
echo
echo "3. (recommended) Add a shell alias:"
echo "      alias vault='python3 $VAULT_ROOT/llmzone/shared/scripts/vault.py'"
echo "   Then: vault check, vault new feature MyFeature, vault new pr MyFeature 1234, etc."
echo
echo "4. Open $VAULT_ROOT in Obsidian. Start with llmzone/START_HERE.md."
echo
echo "Run \`./setup.sh\` again any time to update the GitHub repo default or reinstall the slash command."
