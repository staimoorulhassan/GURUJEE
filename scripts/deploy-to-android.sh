#!/bin/bash
# Phase 4: Deploy GURUJEE to Android/Termux
# Usage: bash deploy-to-android.sh

set -e

ADB="${ANDROID_HOME}/platform-tools/adb"
if [ ! -f "$ADB" ]; then
    ADB="/c/Users/Taimoor/AppData/Local/Android/Sdk/platform-tools/adb.exe"
fi

DEVICE=$(${ADB} devices | grep -E "device$" | head -1 | awk '{print $1}')

if [ -z "$DEVICE" ]; then
    echo "❌ No Android device found. Connect a device and enable ADB."
    exit 1
fi

echo "✅ Device found: $DEVICE"
echo ""

# Phase 4.1: Install dependencies on Termux
echo "=== PHASE 4.1: Installing Termux dependencies ==="
${ADB} shell "apt update"
${ADB} shell "apt install -y python python-pip git curl wget"
${ADB} shell "pip install fastapi uvicorn httpx pydantic pyyaml cryptography psutil"

echo "✅ Dependencies installed"
echo ""

# Phase 4.2: Create Termux home directory structure
echo "=== PHASE 4.2: Setting up directory structure ==="
${ADB} shell "mkdir -p /data/data/com.termux/files/home/GURUJEE"
${ADB} shell "mkdir -p /data/data/com.termux/files/home/GURUJEE/data/{audit,metrics}"
${ADB} shell "mkdir -p /data/data/com.termux/files/home/GURUJEE/config"

echo "✅ Directories created"
echo ""

# Phase 4.3: Push application code
echo "=== PHASE 4.3: Pushing application code ==="
REPO_DIR="/c/Users/Taimoor/source/repos/staimoorulhassan/GURUJEE"

# Push source code
${ADB} push "${REPO_DIR}/gurujee" "/data/data/com.termux/files/home/GURUJEE/" > /dev/null
${ADB} push "${REPO_DIR}/config" "/data/data/com.termux/files/home/GURUJEE/" > /dev/null
${ADB} push "${REPO_DIR}/tests" "/data/data/com.termux/files/home/GURUJEE/" > /dev/null

echo "✅ Application code pushed"
echo ""

# Phase 4.4: Create startup script
echo "=== PHASE 4.4: Creating startup script ==="
${ADB} shell "cat > /data/data/com.termux/files/home/GURUJEE/start.sh << 'STARTUP_EOF'
#!/bin/bash
cd /data/data/com.termux/files/home/GURUJEE
export PYTHONPATH=/data/data/com.termux/files/home/GURUJEE:\$PYTHONPATH
export GURUJEE_DATA_DIR=/data/data/com.termux/files/home/GURUJEE/data

echo '🚀 Starting GURUJEE daemon on Termux (ARM64)...'
python -m gurujee.daemon
STARTUP_EOF
"

${ADB} shell "chmod +x /data/data/com.termux/files/home/GURUJEE/start.sh"

echo "✅ Startup script created"
echo ""

# Phase 4.5: Run initial tests
echo "=== PHASE 4.5: Running tests on device ==="
${ADB} shell "cd /data/data/com.termux/files/home/GURUJEE && python -m pytest tests/test_audit_logger.py -v --tb=short 2>&1" | tail -20

echo ""
echo "✅ Phase 4 setup complete!"
echo ""
echo "=== NEXT STEPS ==="
echo "1. Start daemon: adb shell /data/data/com.termux/files/home/GURUJEE/start.sh"
echo "2. Test SMS: adb shell /data/data/com.termux/files/usr/bin/termux-sms-send -n +1234567890 'Test'"
echo "3. Monitor RAM: adb shell cat /proc/meminfo"
echo "4. Check server: curl http://localhost:7171/api/health"
