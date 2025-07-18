#!/usr/bin/env bash
# check_env.sh  –  verify & bootstrap Python environment for WDMStool

REQUIRED_PKGS=(numpy pandas matplotlib tqdm glob2)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "── Checking for Python 3 ─────────────────────────────────────────────"
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python 3 not found on PATH."
    echo "   Please install Python 3 (≥3.8) and re-run this script."
    exit 1
fi
PYTHON=$(command -v python3)
echo "✅ Found Python: $PYTHON ($(python3 --version))"

echo
echo "── Checking required Python packages ────────────────────────────────"

ALREADY_INSTALLED=()
JUST_INSTALLED=()

for pkg in "${REQUIRED_PKGS[@]}"; do
    if "$PYTHON" - << EOF 2>/dev/null
import importlib.util, sys
sys.exit(0 if importlib.util.find_spec("$pkg") else 1)
EOF
    then
        ALREADY_INSTALLED+=("$pkg")
    else
        echo "Installing missing package: $pkg"
        if "$PYTHON" -m pip install --quiet --user "$pkg"; then
            JUST_INSTALLED+=("$pkg")
        else
            # macOS / Homebrew Python may be “externally managed”; try again with --break-system-packages
            "$PYTHON" -m pip install --quiet --user --break-system-packages "$pkg" && JUST_INSTALLED+=("$pkg")
        fi
    fi
done

echo
echo "── Summary ───────────────────────────────────────────────────────────"
[[ ${#ALREADY_INSTALLED[@]} -gt 0 ]] && \
    echo "✅ Already present:  ${ALREADY_INSTALLED[*]}"
[[ ${#JUST_INSTALLED[@]}    -gt 0 ]] && \
    echo "📦 Installed now:    ${JUST_INSTALLED[*]}"
[[ ${#JUST_INSTALLED[@]} -eq 0 ]] && \
    echo "🎉 All requirements were already satisfied."

echo "Done."

 # Ensure primary scripts are executable
 chmod +x "$SCRIPT_DIR/main.sh"        # launcher
 chmod +x "$SCRIPT_DIR/check_env.sh"   # this setup script
echo "───────────────────────────────────────────────────────────────────────"
echo
echo "── Setting up shell alias ───────────────────────────────────────────"
ALIAS_LINE="alias wdmstool=\"$SCRIPT_DIR/main.sh\""
ZSHRC="$HOME/.zshrc"

if [ -w "$ZSHRC" ]; then
    if grep -Fxq "$ALIAS_LINE" "$ZSHRC"; then
        echo "✅ Alias 'wdmstool' already present in $ZSHRC"
    else
        echo "alias wdmstool=\"$SCRIPT_DIR/main.sh\"" >> "$ZSHRC"
        echo "✅ Added alias 'wdmstool' to $ZSHRC"
        ADDED_ALIAS=true
    fi
else
    echo "⚠️  Could not write to $ZSHRC (permission denied)."
    echo "    Add the following line manually if desired:"
    echo "    $ALIAS_LINE"
fi

if [ "$ADDED_ALIAS" = true ]; then
    echo "ℹ️  Run 'source $ZSHRC' or open a new terminal to start using the 'wdmstool' command."
    echo "Enjoy using WDMStool!"
fi
echo "───────────────────────────────────────────────────────────────────────"
exit 0
# ── End of check_env.sh ───────────────────────────────────────────────────