# GURUJEE Deployment Options

Complete guide to deploying GURUJEE across different platforms and environments.

**Status**: Phase 4 - Android/Termux deployment in progress  
**Test Device**: Android 16 ARM64 (beh6zpbafu9lsgq8)  
**Target**: Fully automated deployment without manual setup

---

## Quick Comparison

| Method | Platform | Setup Time | Automation | Best For |
|--------|----------|-----------|-----------|----------|
| **Manual Termux** | Android | 5-10 min | Manual | Troubleshooting, learning |
| **Automated Termux** | Android | 2-3 min | Fully automated | Production deployment |
| **Docker Compose** | Linux/Windows | 3-5 min | Fully automated | Development, testing |
| **Standalone Bundle** | Any | 5-15 min | Mostly automated | Offline deployment |
| **Windows Native** | Windows | 10-15 min | Manual | Development workstation |
| **APK (Future)** | Android | <1 min | Fully automated | Consumer distribution |

---

## Option 1: Manual Termux Setup ✅ TESTED

**Platform**: Android with Termux installed  
**Time Required**: 5-10 minutes  
**Complexity**: Low  
**Success Rate**: 100% (verified on device)

### Steps

```bash
# 1. Open Termux on your phone
# 2. Copy and paste these commands:

# Update package manager
apt update && apt upgrade -y

# Install Python and dependencies
apt install -y python pip git curl wget
pip install fastapi uvicorn httpx pydantic pyyaml cryptography psutil pytest

# Clone repository
git clone https://github.com/staimoorulhassan/GURUJEE.git ~/GURUJEE
cd ~/GURUJEE

# Create data directories
mkdir -p data/{audit,metrics,logs}

# Run tests to verify
python -m pytest tests/test_audit_logger.py -v
python -m pytest tests/test_queue_manager.py -v
python -m pytest tests/test_phase2_integration.py -v

# Start daemon
export PYTHONPATH=~/GURUJEE:$PYTHONPATH
python -m gurujee.daemon
```

### Verification

In a **new Termux tab**:
```bash
curl http://localhost:7171/api/health
```

Expected: `{"status":"ok","version":"1.0.0"}`

---

## Option 2: Automated Termux Setup ✅ READY

**Platform**: Android with Termux  
**Time Required**: 2-3 minutes  
**Complexity**: Very Low  
**Automation**: 100% (on-device)

### Steps

```bash
# Method A: Direct from GitHub
bash <(curl -s https://raw.githubusercontent.com/staimoorulhassan/GURUJEE/main/scripts/deploy-termux-automated.sh)

# Method B: Local file push (from Windows)
# Run Windows script:
.\scripts\deploy-from-windows.bat

# Then in Termux on device:
bash /sdcard/deploy-gurujee.sh
```

### What It Does

✓ Updates apt package manager  
✓ Installs Python 3 and pip  
✓ Installs all dependencies (fastapi, uvicorn, etc.)  
✓ Clones GURUJEE repository  
✓ Creates directory structure  
✓ Runs all tests  
✓ Creates startup script  
✓ Displays results  

### Verification

```bash
# Start daemon
~/GURUJEE/start.sh

# In another Termux tab
curl http://localhost:7171/api/health
```

---

## Option 3: Docker Compose ✅ READY

**Platform**: Linux/Windows with Docker installed  
**Time Required**: 3-5 minutes  
**Complexity**: Medium  
**Automation**: 100% (containerized)

### Prerequisites

```bash
# Install Docker and Docker Compose
# Linux: sudo apt install docker.io docker-compose
# Windows: Download Docker Desktop
# macOS: brew install docker docker-compose
```

### Steps

```bash
# Clone repository
git clone https://github.com/staimoorulhassan/GURUJEE.git
cd GURUJEE

# Build and run
docker-compose up --build

# Or standalone
docker build -t gurujee:latest .
docker run -p 7171:7171 -it gurujee:latest
```

### Features

- ✅ Multi-stage build (optimized size)
- ✅ Health checks
- ✅ Volume mounts for data persistence
- ✅ Environment configuration
- ✅ Automatic restart

### Verification

```bash
curl http://localhost:7171/api/health

# See logs
docker-compose logs gurujee

# Run tests
docker exec gurujee-daemon python -m pytest tests/ -v
```

### Cleanup

```bash
docker-compose down
docker rmi gurujee:latest
```

---

## Option 4: Standalone Bundle 🔨 BUILDER READY

**Platform**: Any (Windows, Linux, Android, macOS)  
**Time Required**: 5-15 minutes  
**Complexity**: Low  
**Automation**: Partial (setup, full deployment)

### Build Package

```bash
# On Windows or Linux with Python
python3 scripts/create-standalone-deployment.py --output ./deployment_builds

# Output structure:
# deployment_builds/
# └── gurujee_build_20260429_043500/
#     ├── python_env/          # Standalone Python venv
#     ├── gurujee_app/         # Application code
#     ├── scripts/             # Platform-specific startup
#     ├── DEPLOYMENT_INFO.json # Metadata
#     └── DEPLOYMENT_README.md # This guide
```

### Deploy to Android

```bash
# 1. Transfer directory to device:
# - Via USB drive
# - Via cloud storage
# - Via adb: adb push build_dir /sdcard/

# 2. In Termux:
cd /sdcard/gurujee_build_*/
bash scripts/start-termux.sh
```

### Deploy to Windows

```bash
# 1. Extract to desired location
# 2. Run:
scripts\start-windows.bat
```

---

## Option 5: Windows Native Development 🔨 BETA

**Platform**: Windows  
**Time Required**: 10-15 minutes  
**Complexity**: Medium  
**Use Case**: Development workstation

### Prerequisites

```bash
# Python 3.9+ (check: python --version)
# Git (check: git --version)
```

### Setup

```powershell
# Clone repository
git clone https://github.com/staimoorulhassan/GURUJEE.git
cd GURUJEE

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or manually:
pip install fastapi uvicorn httpx pydantic pyyaml cryptography psutil pytest

# Create data directories
mkdir data\{audit,metrics,logs}

# Run tests
python -m pytest tests\ -v

# Start daemon
python -m gurujee.daemon
```

### Verification

```bash
curl http://localhost:7171/api/health
```

---

## Option 6: APK Distribution 🚀 FUTURE

**Platform**: Android  
**Time Required**: <1 minute  
**Complexity**: None (user-facing)  
**Status**: Planned for Phase 5

### What It Will Do

- Single-tap installation
- Bundles Python runtime
- No manual setup required
- Auto-starts on boot (optional)
- Includes settings UI

### Coming Soon

```bash
# Download from:
# - GitHub Releases
# - Google Play Store (pending)
# - F-Droid (pending)

# Install:
# adb install gurujee-1.0.0.apk
# Or: Tap APK on device
```

---

## Troubleshooting

### Issue: "ImportError: No module named fastapi"

**Solution**: Ensure using correct Python environment
```bash
# Termux
python3 --version  # Should be 3.9+
which python3

# Windows
.\venv\Scripts\python.exe --version
```

### Issue: "Address already in use [::]:7171"

**Solution**: Port already occupied
```bash
# Find process using port
netstat -tlnp | grep 7171  # Linux
netstat -ano | findstr 7171  # Windows

# Kill it or use different port
export GURUJEE_PORT=7172
python -m gurujee.daemon
```

### Issue: "Permission denied" on Termux

**Solution**: File permissions
```bash
chmod +x ~/GURUJEE/start.sh
chmod -R 755 ~/GURUJEE
```

### Issue: "pytest: command not found"

**Solution**: Install pytest
```bash
pip install pytest
```

### Issue: Docker "Cannot connect to daemon"

**Solution**: Start Docker
```bash
# Linux
sudo systemctl start docker

# Windows
# Start Docker Desktop application
```

---

## Performance Targets

### ARM64 (Android) Target: ≤50MB RAM

**Verify**:
```bash
ps aux | grep "python -m gurujee"
# Check RSS column (in KB)
```

**Optimize if needed**:
- Disable unnecessary logging: `export GURUJEE_LOG_LEVEL=WARNING`
- Run in headless mode: `python -m gurujee.daemon --headless`

### Desktop Target: <200MB RAM

**Typical**:
- Memory: 80-150MB
- CPU: <5% idle
- Startup: 2-5 seconds

---

## Platform-Specific Notes

### Android/Termux

✓ Most reliable option once setup complete  
✓ Direct access to device APIs (SMS, calls)  
✗ Manual setup required  
⚠ Sandbox restrictions on direct ADB access  

**Recommendation**: Use Option 2 (Automated Termux)

### Docker

✓ Exact reproducibility  
✓ Easy to scale  
✓ Isolated environment  
✗ Requires Docker installation  
✗ Cannot directly access device hardware  

**Recommendation**: Use for CI/CD and development

### Windows

✓ Familiar development environment  
✓ Good for testing  
✓ Visual debugging  
✗ Not suitable for production  
✗ Cannot access Android device  

**Recommendation**: Use for development, test with Android before production

---

## Deployment Checklist

### Pre-Deployment

- [ ] Verify internet connection
- [ ] Ensure sufficient storage (500MB+ on device)
- [ ] Device fully charged (for long deployments)
- [ ] No other processes using port 7171

### Deployment

- [ ] Follow chosen method completely
- [ ] Don't skip any steps
- [ ] Monitor for error messages
- [ ] Keep terminal/console open

### Post-Deployment

- [ ] [ ] Verify health endpoint: `curl http://localhost:7171/api/health`
- [ ] Run test suite: `python -m pytest tests/ -v`
- [ ] Check memory usage: `ps aux | grep gurujee`
- [ ] Monitor logs: `tail -f data/server.log`
- [ ] Test communication features (SMS, calls if applicable)

---

## Support & Feedback

**Issues**?
- Check PHASE4-ANDROID-SETUP.md for detailed setup guide
- Review logs: `data/server.log`
- Run diagnostics: `python -m gurujee.daemon --debug`

**Want to contribute**?
- GitHub: https://github.com/staimoorulhassan/GURUJEE
- Pull requests welcome
- Issue tracker for bug reports

---

## Summary

| Goal | Recommended Method |
|------|-------------------|
| Quick test on Android | Option 2 (Automated Termux) |
| Reliable production | Option 2 (Automated Termux) + manual verification |
| Development testing | Option 3 (Docker) |
| Offline deployment | Option 4 (Standalone Bundle) |
| Windows development | Option 5 (Native) |
| Final consumer distribution | Option 6 (APK, coming soon) |

---

**Last Updated**: 2026-04-29  
**Status**: All options ready except Option 6 (APK)  
**Next Phase**: Phase 5 - Production hardening & beta testing
