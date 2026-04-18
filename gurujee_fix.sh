#!/data/data/com.termux/files/usr/bin/bash
# GURUJEE daemon fix script — idempotent recovery
set -e

GURUJEE_DIR="${HOME}/gurujee"

echo "=== GURUJEE Fix Script ==="

# Install native packages via pkg (avoids Rust/compile failures for cryptography)
echo "[1/5] Native packages..."
pkg install -y libffi openssl python-cryptography clang make 2>&1 | tail -2

# Upgrade setuptools/wheel using --no-index is not possible, use --upgrade with retry
echo "[2/5] Upgrading pip + setuptools..."
pip install --upgrade pip 2>&1 | tail -2
pip install --upgrade "setuptools" wheel 2>&1 | tail -2

echo "[3/5] Python dependencies (skipping audio packages that need native compile)..."
pip install --prefer-binary \
    openai anthropic fastapi uvicorn httpx python-multipart \
    textual rich PyYAML "ruamel.yaml" tenacity \
    pytest pytest-asyncio pytest-cov responses 2>&1 | tail -5

# --no-build-isolation: skip isolated build env (avoids re-downloading setuptools)
# --no-deps: all real deps already installed above; skip faster-whisper/elevenlabs
echo "[4/5] Installing GURUJEE package (no-deps, no-build-isolation)..."
pip install --no-deps --no-build-isolation -e "$GURUJEE_DIR"

# Enable allow-external-apps
TERMUX_PROPS="$HOME/.termux/termux.properties"
mkdir -p "$HOME/.termux"
grep -q "allow-external-apps" "$TERMUX_PROPS" 2>/dev/null || \
    echo "allow-external-apps = true" >> "$TERMUX_PROPS"

# Start daemon
echo "[5/5] Starting daemon..."
mkdir -p "$GURUJEE_DIR/data"
source "${HOME}/.gurujee.env" 2>/dev/null || true
cd "$GURUJEE_DIR"
pkill -f "gurujee --headless" 2>/dev/null || true
nohup python -m gurujee --headless >> "$GURUJEE_DIR/data/boot.log" 2>&1 &
echo "PID $! — waiting 5s..."
sleep 5

if curl -s http://127.0.0.1:7171/health 2>/dev/null | grep -q "ready"; then
    echo "=== SUCCESS: GURUJEE daemon running. Switch to the GURUJEE app. ==="
else
    echo "=== Still starting — boot log: ==="
    tail -20 "$GURUJEE_DIR/data/boot.log" 2>/dev/null || echo "(no log yet)"
fi
