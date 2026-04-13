#!/data/data/com.termux/files/usr/bin/bash
# GURUJEE install.sh — idempotent Termux bootstrap
# Usage: curl -fsSL <url>/install.sh | bash
#        GURUJEE_INSTALL_DIR=$HOME/mygurujee curl -fsSL <url>/install.sh | bash
set -euo pipefail

REPO_URL="https://github.com/staimoorulhassan/GURUJEE.git"

# Determine install directory.
# BASH_SOURCE[0] is empty or "/dev/stdin" when the script is piped, so we
# cannot use dirname to locate the script itself. Instead:
#   1. Honour an explicit caller-supplied override via GURUJEE_INSTALL_DIR.
#   2. Fall back to $HOME/gurujee for a predictable, piped-install location.
if [[ -n "${GURUJEE_INSTALL_DIR:-}" ]]; then
    GURUJEE_DIR="$(cd "$GURUJEE_INSTALL_DIR" 2>/dev/null && pwd || echo "$GURUJEE_INSTALL_DIR")"
elif [[ -n "${BASH_SOURCE[0]:-}" && "${BASH_SOURCE[0]}" != "/dev/stdin" && -e "${BASH_SOURCE[0]}" ]]; then
    # Running as a local file (e.g. bash install.sh); use the script's own directory.
    GURUJEE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
    GURUJEE_DIR="${HOME}/gurujee"
fi

echo "=== GURUJEE Installer ==="
echo "Install directory: $GURUJEE_DIR"

# Update and install base packages
pkg update -y && pkg upgrade -y
pkg install -y python git

# Install Rust toolchain for Python packages requiring compilation
pkg install -y rust binutils clang make
echo "Rust installed: $(cargo --version)"

# Clone or update repo
if [ -d "$GURUJEE_DIR/.git" ]; then
    # Verify the directory is actually the GURUJEE repo before pulling.
    REMOTE_URL="$(git -C "$GURUJEE_DIR" remote get-url origin 2>/dev/null || echo "")"
    if echo "$REMOTE_URL" | grep -qi "staimoorulhassan/GURUJEE"; then
        echo "Existing install detected — pulling latest..."
        git -C "$GURUJEE_DIR" pull --ff-only
    else
        echo "Error: $GURUJEE_DIR contains a git repo with a different remote:" >&2
        echo "  found:    $REMOTE_URL" >&2
        echo "  expected: $REPO_URL" >&2
        echo "Set GURUJEE_INSTALL_DIR to a different path and re-run." >&2
        exit 1
    fi
else
    echo "Fresh install — cloning into $GURUJEE_DIR ..."
    git clone "$REPO_URL" "$GURUJEE_DIR"
fi

# Install Python dependencies
pip install -r "$GURUJEE_DIR/requirements.txt"

# Install GURUJEE package in development mode
echo "Installing GURUJEE package..."
pip install -e "$GURUJEE_DIR"
if [ $? -ne 0 ]; then
    echo "Failed to install GURUJEE package. Please check the error above."
    exit 1
fi

# Create data directory if missing
mkdir -p "$GURUJEE_DIR/data"

echo "=== Starting setup wizard ==="
cd "$GURUJEE_DIR"
python -c "from gurujee.setup.wizard import SetupWizard; SetupWizard().run()"
