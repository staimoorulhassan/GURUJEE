#!/bin/bash
# Automated Termux Deployment with Comprehensive Setup
# This script runs ON THE ANDROID DEVICE from within Termux
# Usage: bash deploy-termux-automated.sh

set -e

echo "╔════════════════════════════════════════════════════╗"
echo "║  GURUJEE Phase 4: Automated Termux Deployment     ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_step() {
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}$1${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Step 1: Check if running in Termux
log_step "STEP 1: Verifying Termux Environment"
if [ ! -d "$PREFIX" ]; then
    log_error "This script must be run from within Termux!"
    exit 1
fi
log_success "Running in Termux (PREFIX=$PREFIX)"
log_info "Architecture: $(getprop ro.product.cpu.abi)"

# Step 2: Update package manager
log_step "STEP 2: Updating Package Manager"
log_info "Running apt update..."
apt update > /dev/null 2>&1 || {
    log_error "apt update failed"
    exit 1
}
log_success "Package manager updated"

# Step 3: Install Python and dependencies
log_step "STEP 3: Installing Python & Core Dependencies"
log_info "Installing Python, pip, git, curl..."
apt install -y python pip git curl wget > /dev/null 2>&1 || {
    log_error "Failed to install system packages"
    exit 1
}
log_success "System packages installed"

# Verify Python
PYTHON_VERSION=$(python3 --version 2>&1)
log_success "Python available: $PYTHON_VERSION"

# Step 4: Install Python packages
log_step "STEP 4: Installing Python Packages"
log_info "Installing: fastapi, uvicorn, pydantic, pyyaml, cryptography, psutil, pytest..."

PACKAGES="fastapi uvicorn httpx pydantic pyyaml cryptography psutil pytest"
pip install $PACKAGES > /dev/null 2>&1 || {
    log_error "pip install failed"
    exit 1
}
log_success "All Python packages installed"

# Step 5: Clone or verify GURUJEE code
log_step "STEP 5: Setting up GURUJEE Application"
GURUJEE_HOME="$HOME/GURUJEE"

if [ -d "$GURUJEE_HOME" ]; then
    log_info "GURUJEE directory already exists at $GURUJEE_HOME"
    log_info "Updating from remote..."
    cd "$GURUJEE_HOME"
    git pull origin main 2>&1 | head -5
else
    log_info "Cloning GURUJEE from GitHub..."
    git clone https://github.com/staimoorulhassan/GURUJEE.git "$GURUJEE_HOME" 2>&1 | grep -E "Cloning|Resolving"
fi

log_success "GURUJEE available at $GURUJEE_HOME"

# Step 6: Create directory structure
log_step "STEP 6: Creating Directory Structure"
mkdir -p "$GURUJEE_HOME/data/audit"
mkdir -p "$GURUJEE_HOME/data/metrics"
mkdir -p "$GURUJEE_HOME/data/logs"
log_success "Data directories created"

# Step 7: Set environment variables
log_step "STEP 7: Configuring Environment"
cat > "$HOME/.gurujee_env" << 'ENVEOF'
export PYTHONPATH=$HOME/GURUJEE:$PYTHONPATH
export GURUJEE_DATA_DIR=$HOME/GURUJEE/data
export GURUJEE_LOG_LEVEL=INFO
ENVEOF
log_success "Environment file created at ~/.gurujee_env"

# Step 8: Run tests
log_step "STEP 8: Running Verification Tests"
cd "$GURUJEE_HOME"

log_info "Running audit logger tests..."
python -m pytest tests/test_audit_logger.py -v --tb=short 2>&1 | tail -5

log_info "Running queue manager tests..."
python -m pytest tests/test_queue_manager.py -v --tb=short 2>&1 | tail -5

log_info "Running integration tests..."
python -m pytest tests/test_phase2_integration.py -v --tb=short 2>&1 | tail -5

log_success "All tests completed"

# Step 9: Create startup script
log_step "STEP 9: Creating Startup Script"
cat > "$GURUJEE_HOME/start.sh" << 'STARTEOF'
#!/bin/bash
# GURUJEE Startup Script for Termux

cd ~/GURUJEE
source ~/.gurujee_env

echo "🚀 Starting GURUJEE daemon on Android Termux (ARM64)..."
echo "📊 Data directory: $GURUJEE_DATA_DIR"
echo "🔗 Server: http://localhost:7171"
echo ""
echo "Press Ctrl+C to stop the daemon"
echo ""

python -m gurujee.daemon
STARTEOF

chmod +x "$GURUJEE_HOME/start.sh"
log_success "Startup script created and made executable"

# Step 10: Display completion info
log_step "✨ DEPLOYMENT COMPLETE ✨"
echo ""
echo -e "${GREEN}GURUJEE is ready to run!${NC}"
echo ""
echo "📋 To start the daemon:"
echo "   ~/GURUJEE/start.sh"
echo ""
echo "📋 Or manually:"
echo "   source ~/.gurujee_env"
echo "   cd ~/GURUJEE"
echo "   python -m gurujee.daemon"
echo ""
echo "🔗 Once running, access at: http://localhost:7171/api/health"
echo ""
echo "📊 Memory usage should be < 50MB (ARM64 target)"
echo "   Check with: ps aux | grep 'python -m gurujee'"
echo ""
echo "📝 Logs are saved to: $GURUJEE_DATA_DIR/server.log"
echo ""

# Show performance baseline
log_step "Performance Baseline"
if command -v free &> /dev/null; then
    free -h
fi
log_info "Current process list:"
ps aux | grep -E "python|termux" | grep -v grep | head -3

echo ""
log_success "Setup complete! Run '~/GURUJEE/start.sh' to begin"
