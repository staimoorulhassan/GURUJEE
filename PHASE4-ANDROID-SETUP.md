# Phase 4: Android/Termux Deployment - Manual Setup Guide

## Situation
Due to Android permission restrictions, GURUJEE application files have been deployed to `/sdcard/GURUJEE/` on your device (beh6zpbafu9lsgq8). To complete Phase 4 testing, complete the following steps **from within Termux** on the device.

## Device Specs Verified
- **Model**: 23117RA68G (ARM64)
- **Android**: 16 (API 36)
- **RAM**: 12GB
- **Termux**: Installed ✅
- **Termux:API**: Installed ✅
- **ADB**: Connected and responding ✅

---

## Setup Steps (Run in Termux Terminal on Device)

### 1. Copy Application Files from SD Card
```bash
mkdir -p ~/GURUJEE
cp -r /sdcard/GURUJEE/* ~/GURUJEE/
cd ~/GURUJEE
ls -la  # Verify: should see gurujee/, config/, tests/
```

### 2. Install Python Dependencies
```bash
apt update
apt install -y python pip git curl wget
pip install fastapi uvicorn httpx pydantic pyyaml cryptography psutil pytest
```

### 3. Create Directory Structure
```bash
mkdir -p ~/GURUJEE/data/{audit,metrics}
export GURUJEE_DATA_DIR=~/GURUJEE/data
```

### 4. Verify Installation
```bash
python3 --version  # Should be Python 3.x
pip list | grep -E "fastapi|uvicorn|pydantic"  # Verify packages
```

### 5. Run Unit Tests
```bash
cd ~/GURUJEE
python -m pytest tests/test_audit_logger.py -v
python -m pytest tests/test_queue_manager.py -v
python -m pytest tests/test_phase2_integration.py -v
```

### 6. Start GURUJEE Daemon
```bash
export PYTHONPATH=~/GURUJEE:$PYTHONPATH
export GURUJEE_DATA_DIR=~/GURUJEE/data
python -m gurujee.daemon
```

**Expected Output**:
```
INFO:uvicorn.server:Uvicorn running on http://0.0.0.0:7171
```

### 7. Test from Another Terminal (while daemon runs)
```bash
# In a new Termux terminal tab:
curl http://localhost:7171/api/health

# Expected response:
{"status":"ok","version":"1.0.0"}
```

### 8. Test SMS Automation (if SMS provider configured)
```bash
# Requires Termux:API setup
termux-sms-send -n +15551234567 "Test message from GURUJEE"
```

---

## Performance Validation (ARM64 ≤50MB Target)

```bash
# Monitor memory usage while daemon runs:
while true; do
  ps aux | grep "python -m gurujee" | grep -v grep | awk '{print "RSS: " $6 " KB"}'
  sleep 5
done

# Alternative - check /proc/meminfo
cat /proc/meminfo | grep -E "Mem|Available"
```

---

## File Locations

- **Application Code**: `/sdcard/GURUJEE/gurujee/`
- **Configuration**: `/sdcard/GURUJEE/config/`
- **Tests**: `/sdcard/GURUJEE/tests/`
- **Data Directory**: `~/GURUJEE/data/` (audit logs, metrics)
- **Server Log**: `~/GURUJEE/data/server.log`

---

## Troubleshooting

### "ImportError: No module named fastapi"
```bash
pip install fastapi uvicorn pydantic pyyaml cryptography
```

### "ModuleNotFoundError: No module named 'gurujee'"
```bash
export PYTHONPATH=~/GURUJEE:$PYTHONPATH
python -m gurujee.daemon
```

### "Permission denied" when copying from /sdcard
```bash
# Give yourself write permission:
chmod 755 ~/GURUJEE
```

### Connection refused on port 7171
The daemon may not have started. Check for errors in the terminal output.

---

## Phase 4 Completion Checklist

- [ ] Files copied to `~/GURUJEE`
- [ ] Python 3 and pip installed
- [ ] Dependencies installed (`fastapi`, `uvicorn`, `pydantic`, etc.)
- [ ] Unit tests pass (all 27/27 passing on desktop, should match on device)
- [ ] Daemon starts without errors
- [ ] `/api/health` endpoint responds
- [ ] Memory usage < 50MB (ARM64 gate)
- [ ] SMS automation tested (optional, requires SMS provider config)

---

## Next Steps (Phase 5)

Once Phase 4 testing is complete on device:
1. Document any performance issues or compatibility notes
2. Run full integration test suite
3. Prepare for beta testing (user feedback cycle)
4. Begin production hardening (security audit, optimization)

---

**Device**: beh6zpbafu9lsgq8  
**Architecture**: ARM64  
**Status**: Ready for manual Termux setup  
**Last Updated**: 2026-04-29
