#!/data/data/com.termux/files/usr/bin/bash
# GURUJEE install.sh — idempotent Termux bootstrap
# Usage: curl -fsSL <url>/install.sh | bash
set -e

GURUJEE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== GURUJEE Installer ==="

# Update and install base packages
pkg update -y && pkg upgrade -y
pkg install -y python git

# Clone or update repo
if [ -d "$GURUJEE_DIR/.git" ]; then
    echo "Existing install detected — pulling latest..."
    git -C "$GURUJEE_DIR" pull --ff-only
else
    echo "Fresh install — cloning..."
    git clone https://github.com/gurujee/gurujee.git "$GURUJEE_DIR"
fi

# Install Python dependencies
pip install -r "$GURUJEE_DIR/requirements.txt"

# Create data directory if missing
mkdir -p "$GURUJEE_DIR/data"

echo "=== Starting setup wizard ==="
cd "$GURUJEE_DIR"
python -m gurujee.setup
