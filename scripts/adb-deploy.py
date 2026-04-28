#!/usr/bin/env python3
"""
Automated ADB Deployment Helper
Deploys GURUJEE to connected Android device via ADB

Usage:
    python adb-deploy.py [--device DEVICE_ID] [--auto-run]
"""

import subprocess
import os
import sys
import time
from pathlib import Path

class ADBDeployment:
    """Manage GURUJEE deployment via ADB"""

    def __init__(self):
        self.repo_root = Path(__file__).parent.parent
        self.script_path = self.repo_root / "scripts" / "deploy-termux-automated.sh"
        self.adb = self._find_adb()
        self.device = None

    def log(self, message, level="INFO"):
        """Colored logging"""
        colors = {
            "INFO": "\033[94m",
            "SUCCESS": "\033[92m",
            "ERROR": "\033[91m",
            "WARNING": "\033[93m"
        }
        reset = "\033[0m"
        symbol = {"INFO": "[*]", "SUCCESS": "[+]", "ERROR": "[-]", "WARNING": "[!]"}.get(level)
        print("{}{} {}{}".format(colors.get(level, ''), symbol, message, reset))

    def _find_adb(self):
        """Locate ADB executable"""
        # Try common locations
        candidates = [
            Path(os.environ.get("ANDROID_HOME", "")) / "platform-tools" / "adb.exe",
            Path(os.path.expanduser("~")) / "AppData" / "Local" / "Android" / "Sdk" / "platform-tools" / "adb.exe",
            Path("C:/Users") / os.environ.get("USERNAME", "user") / "AppData" / "Local" / "Android" / "Sdk" / "platform-tools" / "adb.exe",
        ]

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

        # Try PATH
        try:
            result = subprocess.run(["where", "adb.exe"], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split('\n')[0]
        except:
            pass

        return None

    def run(self, cmd):
        """Execute command and return output"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Timeout"
        except Exception as e:
            return -1, "", str(e)

    def check_adb(self):
        """Verify ADB is available"""
        if not self.adb:
            self.log("ADB not found. Please install Android SDK.", "ERROR")
            self.log("Or set ANDROID_HOME environment variable.", "WARNING")
            return False

        self.log(f"ADB found: {self.adb}", "SUCCESS")
        return True

    def get_device(self, device_id=None):
        """Find connected device"""
        cmd = f'"{self.adb}" devices'
        rc, stdout, stderr = self.run(cmd)

        if rc != 0:
            self.log("Failed to get device list", "ERROR")
            return False

        devices = [line.split()[0] for line in stdout.split('\n') if 'device' in line and 'devices' not in line]

        if not devices:
            self.log("No Android devices found. Connect a device and enable ADB.", "ERROR")
            return False

        if device_id:
            if device_id in devices:
                self.device = device_id
                self.log(f"Using specified device: {device_id}", "SUCCESS")
                return True
            else:
                self.log(f"Device {device_id} not found", "ERROR")
                return False

        if len(devices) == 1:
            self.device = devices[0]
            self.log(f"Device found: {self.device}", "SUCCESS")
            return True

        self.log(f"Multiple devices found: {devices}", "WARNING")
        self.device = devices[0]
        self.log(f"Using first device: {self.device}", "INFO")
        return True

    def push_script(self):
        """Push deployment script to device"""
        self.log("Pushing deployment script...", "INFO")

        if not self.script_path.exists():
            self.log(f"Script not found: {self.script_path}", "ERROR")
            return False

        cmd = f'"{self.adb}" -s {self.device} push "{self.script_path}" /sdcard/deploy-gurujee.sh'
        rc, stdout, stderr = self.run(cmd)

        if rc != 0:
            self.log(f"Failed to push script: {stderr}", "ERROR")
            return False

        self.log("Script pushed to /sdcard/deploy-gurujee.sh", "SUCCESS")
        return True

    def display_instructions(self):
        """Display next steps to user"""
        print("\n" + "=" * 60)
        print("NEXT STEPS - Complete on Your Android Device")
        print("=" * 60 + "\n")

        print("STEP 1: Open Termux app on your device")
        print("")
        print("STEP 2: Copy and paste this command:")
        print("")
        print("    bash /sdcard/deploy-gurujee.sh")
        print("")
        print("STEP 3: Wait 2-3 minutes for installation to complete")
        print("")
        print("STEP 4: Start the daemon:")
        print("")
        print("    ~/GURUJEE/start.sh")
        print("")
        print("STEP 5: Verify in another Termux tab:")
        print("")
        print("    curl http://localhost:7171/api/health")
        print("")
        print("=" * 60 + "\n")

    def deploy(self, device_id=None, auto_run=False):
        """Execute deployment"""
        print("\n" + "=" * 60)
        print("GURUJEE Android ADB Deployment Helper")
        print("=" * 60 + "\n")

        # Step 1: Check ADB
        self.log("Checking ADB installation...", "INFO")
        if not self.check_adb():
            return False

        # Step 2: Find device
        self.log("Scanning for connected devices...", "INFO")
        if not self.get_device(device_id=device_id):
            return False

        # Step 3: Push script
        if not self.push_script():
            return False

        # Step 4: Display instructions
        self.display_instructions()

        if auto_run:
            self.log("Attempting automatic execution (may not work due to sandbox)...", "WARNING")
            time.sleep(2)
            cmd = f'"{self.adb}" -s {self.device} shell bash /sdcard/deploy-gurujee.sh'
            rc, stdout, stderr = self.run(cmd)
            if rc == 0:
                self.log("Script executed successfully!", "SUCCESS")
                print(stdout)
            else:
                self.log("Automatic execution not available (expected). Execute manually on device.", "WARNING")

        self.log("Deployment setup complete!", "SUCCESS")
        return True

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Deploy GURUJEE to Android device via ADB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python adb-deploy.py
  python adb-deploy.py --device beh6zpbafu9lsgq8
  python adb-deploy.py --auto-run
        """
    )
    parser.add_argument("--device", help="Specific device ID")
    parser.add_argument("--auto-run", action="store_true", help="Attempt automatic execution")

    args = parser.parse_args()

    deployer = ADBDeployment()
    success = deployer.deploy(device_id=args.device, auto_run=args.auto_run)

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
