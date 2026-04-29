# Step 3 Failed - Manual Installation Guide

If the automated script fails at Step 3 (installing system packages), follow these manual steps in Termux.

---

## Quick Diagnostic

First, let's find out what went wrong:

```bash
# Check Termux status
termux-info

# Check storage
df -h

# Check apt
apt update
```

**Share the error output** - that will help debug the exact issue.

---

## Common Issues & Fixes

### Issue 1: "Unable to locate package python" or "apt not found"

**Cause**: Termux not properly initialized

**Fix**:
```bash
# Run this FIRST
termux-setup-storage

# Wait for permission prompt, then:
apt update --fix-missing

# Try again:
apt install -y python pip
```

---

### Issue 2: Network/Mirror Error

**Cause**: Default mirror is slow or down

**Fix**:
```bash
# Change mirror interactively
termux-change-repo

# Select: Main repository
# Choose: Albatross, Brics, or another mirror

# Then retry
apt update
apt install -y python pip git curl wget
```

---

### Issue 3: "No space left on device"

**Cause**: Not enough storage for packages

**Fix**:
```bash
# Check available space
df -h

# Should have 500MB+ free in /data
# If low, delete old APKs or other unused files
```

---

### Issue 4: Slow/Hanging apt

**Cause**: Timeout or network latency

**Fix**:
```bash
# Install packages one at a time (slower but more reliable)
apt install -y python
apt install -y python-pip
apt install -y git
apt install -y curl
apt install -y wget
```

---

## Manual Step-by-Step Installation

If you want to skip the script entirely, run these commands manually in Termux:

### Step 1: Initialize Termux
```bash
termux-setup-storage
apt update
```

### Step 2: Install Python
```bash
apt install -y python
python --version  # Should show Python 3.x
```

### Step 3: Install pip
```bash
apt install -y python-pip
pip --version   # Should show pip version
```

### Step 4: Install other tools
```bash
apt install -y git curl wget
```

### Step 5: Install Python dependencies
```bash
pip install fastapi
pip install uvicorn
pip install httpx
pip install pydantic
pip install pyyaml
pip install cryptography
pip install psutil
pip install pytest
```

### Step 6: Clone GURUJEE
```bash
git clone https://github.com/staimoorulhassan/GURUJEE.git ~/GURUJEE
cd ~/GURUJEE
```

### Step 7: Create data directories
```bash
mkdir -p data/audit
mkdir -p data/metrics
mkdir -p data/logs
```

### Step 8: Run tests
```bash
python -m pytest tests/test_audit_logger.py -v
python -m pytest tests/test_queue_manager.py -v
```

### Step 9: Start daemon
```bash
export PYTHONPATH=~/GURUJEE:$PYTHONPATH
export GURUJEE_DATA_DIR=~/GURUJEE/data
python -m gurujee.daemon
```

### Step 10: Verify (in another Termux tab)
```bash
curl http://localhost:7171/api/health
```

Expected response:
```json
{"status":"ok","version":"1.0.0"}
```

---

## If You Hit an Error

### At Step 1-2 (apt)
```bash
# Try alternative mirror
termux-change-repo

# Or try:
apt update --fix-missing
apt upgrade -y
```

### At Step 3 (pip install)
```bash
# Install individually instead of all at once
pip install fastapi  # Wait for this to finish
pip install uvicorn  # Then this
pip install pydantic # Then this, etc.
```

### At Step 5 (git clone)
```bash
# Check internet connection
ping 8.8.8.8

# Or try with different git protocol
git clone https://github.com/staimoorulhassan/GURUJEE.git ~/GURUJEE
# If that fails, try:
git clone --depth 1 https://github.com/staimoorulhassan/GURUJEE.git ~/GURUJEE
```

### At Step 9 (daemon start)
```bash
# Check for errors
python -m gurujee.daemon --verbose

# Or check Python can import modules
python -c "import fastapi; print('fastapi OK')"
python -c "import uvicorn; print('uvicorn OK')"
```

---

## What to Share If It Fails

To get help debugging, please provide:

1. **The exact error message** (copy entire error output)
2. **What step it failed on** (1-10)
3. **Your device specs**:
   ```bash
   termux-info
   ```
4. **Available storage**:
   ```bash
   df -h
   ```
5. **apt status**:
   ```bash
   apt update 2>&1 | head -20
   ```

---

## Alternative: Use Docker Instead

If Termux is giving you trouble, test locally with Docker first:

```bash
# On your Windows/Linux machine:
docker-compose up --build

# Verify it works:
curl http://localhost:7171/api/health

# Then deploy to Android using a different method
```

---

## Success Indicators

Once you complete Step 9 (daemon start), you should see:

```
INFO:     Uvicorn running on http://0.0.0.0:7171
INFO:     Application startup complete
```

And in another tab (Step 10):

```bash
curl http://localhost:7171/api/health
{"status":"ok","version":"1.0.0"}
```

If you see these, **deployment is successful!**

---

## Still Stuck?

1. Try the manual steps above (one at a time)
2. Use Docker to verify code works locally first
3. Check device has sufficient storage (500MB+ free)
4. Ensure Termux is up-to-date
5. Consider using alternative Android terminal app if Termux issues persist

---

**Document created**: 2026-04-29  
**For issues**: Provide complete error output + device info
