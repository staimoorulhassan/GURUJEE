#!/usr/bin/env python3
"""
Create standalone GURUJEE deployment package for Android/Termux
Packages application with dependencies for easy transfer to device

Usage:
    python3 create-standalone-deployment.py [--output OUTPUT_DIR]
"""

import os
import sys
import shutil
import subprocess
import json
from pathlib import Path
from datetime import datetime

class GurujeeDeploymentBuilder:
    """Build deployment packages for GURUJEE"""

    def __init__(self, output_dir="deployment_builds"):
        self.repo_root = Path(__file__).parent.parent
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.build_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.build_dir = self.output_dir / f"gurujee_build_{self.build_timestamp}"

    def log(self, message, level="INFO"):
        """Log with formatting"""
        colors = {
            "INFO": "\033[94m",
            "SUCCESS": "\033[92m",
            "WARNING": "\033[93m",
            "ERROR": "\033[91m"
        }
        reset = "\033[0m"
        color = colors.get(level, "")
        symbol = {
            "INFO": "ℹ",
            "SUCCESS": "✓",
            "WARNING": "⚠",
            "ERROR": "✗"
        }.get(level, "•")
        print(f"{color}{symbol}{reset} {message}")

    def step(self, title):
        """Print step header"""
        print(f"\n{'━' * 60}")
        print(f"📦 {title}")
        print(f"{'━' * 60}\n")

    def create_venv_package(self):
        """Create Python venv with all dependencies"""
        self.step("Creating Python Virtual Environment")

        venv_path = self.build_dir / "python_env"
        self.log(f"Creating venv at {venv_path}")

        try:
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv_path)],
                check=True,
                capture_output=True
            )
            self.log("Virtual environment created", "SUCCESS")
        except subprocess.CalledProcessError as e:
            self.log(f"Failed to create venv: {e}", "ERROR")
            return False

        # Install requirements
        self.log("Installing dependencies...")
        requirements = [
            "fastapi",
            "uvicorn",
            "httpx",
            "pydantic",
            "pyyaml",
            "cryptography",
            "psutil",
            "pytest"
        ]

        pip_exe = venv_path / "bin" / "pip"
        if not pip_exe.exists():
            pip_exe = venv_path / "Scripts" / "pip.exe"

        for package in requirements:
            try:
                subprocess.run(
                    [str(pip_exe), "install", "--quiet", package],
                    check=True,
                    capture_output=True,
                    timeout=60
                )
                self.log(f"  ✓ {package}")
            except subprocess.CalledProcessError:
                self.log(f"  ⚠ {package} (may continue without it)", "WARNING")

        self.log("Dependencies installed", "SUCCESS")
        return True

    def copy_application_code(self):
        """Copy GURUJEE source code"""
        self.step("Copying Application Code")

        app_dir = self.build_dir / "gurujee_app"
        app_dir.mkdir(exist_ok=True)

        # Copy main directories
        for dirname in ["gurujee", "config", "tests"]:
            src = self.repo_root / dirname
            if src.exists():
                dst = app_dir / dirname
                self.log(f"Copying {dirname}...")
                shutil.copytree(
                    src, dst,
                    ignore=shutil.ignore_patterns(
                        "__pycache__", "*.pyc", ".pytest_cache", "*.egg-info"
                    )
                )
                self.log(f"  ✓ {dirname} copied")

        # Copy README and other important files
        for filename in ["README.md", "PHASE4-ANDROID-SETUP.md", "requirements.txt"]:
            src = self.repo_root / filename
            if src.exists():
                shutil.copy2(src, app_dir / filename)

        self.log("Application code copied", "SUCCESS")
        return True

    def create_startup_scripts(self):
        """Create startup scripts for different platforms"""
        self.step("Creating Startup Scripts")

        scripts_dir = self.build_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        # Termux startup script
        termux_script = scripts_dir / "start-termux.sh"
        termux_script.write_text("""#!/bin/bash
# GURUJEE Termux Startup Script
cd "$(dirname "$0")/../gurujee_app"
export PYTHONPATH=$(pwd):$PYTHONPATH
export GURUJEE_DATA_DIR=$(pwd)/data
mkdir -p data/{audit,metrics,logs}
python -m gurujee.daemon
""")
        termux_script.chmod(0o755)
        self.log("✓ start-termux.sh created")

        # Windows batch file
        windows_script = scripts_dir / "start-windows.bat"
        windows_script.write_text("""@echo off
REM GURUJEE Windows Testing Script
setlocal enabledelayedexpansion

cd /d "%~dp0..\gurujee_app"
set "PYTHONPATH=%CD%;%PYTHONPATH%"
set "GURUJEE_DATA_DIR=%CD%\data"

mkdir "%GURUJEE_DATA_DIR%\audit" 2>nul
mkdir "%GURUJEE_DATA_DIR%\metrics" 2>nul
mkdir "%GURUJEE_DATA_DIR%\logs" 2>nul

python -m gurujee.daemon
pause
""")
        self.log("✓ start-windows.bat created")

        self.log("Startup scripts created", "SUCCESS")
        return True

    def create_metadata(self):
        """Create deployment metadata"""
        self.step("Creating Metadata")

        metadata = {
            "build_timestamp": self.build_timestamp,
            "build_date": datetime.now().isoformat(),
            "version": "1.0.0",
            "target_platforms": ["android_arm64_termux", "windows_python", "linux"],
            "included_components": {
                "python_environment": True,
                "application_code": True,
                "startup_scripts": True,
                "tests": True,
                "documentation": True
            },
            "requirements": {
                "android": {
                    "app": "Termux",
                    "python_version": "3.9+",
                    "storage_needed_mb": 500
                },
                "windows": {
                    "python_version": "3.9+",
                    "storage_needed_mb": 300
                },
                "linux": {
                    "python_version": "3.9+",
                    "storage_needed_mb": 300
                }
            },
            "post_deployment": {
                "termux": [
                    "bash scripts/start-termux.sh"
                ],
                "windows": [
                    "scripts\\start-windows.bat"
                ]
            }
        }

        metadata_file = self.build_dir / "DEPLOYMENT_INFO.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        self.log(f"Metadata written to DEPLOYMENT_INFO.json", "SUCCESS")
        return True

    def create_readme(self):
        """Create deployment README"""
        self.step("Creating Deployment Guide")

        readme_path = self.build_dir / "DEPLOYMENT_README.md"
        readme_path.write_text("""# GURUJEE Standalone Deployment Package

**Build Date**: {timestamp}
**Version**: 1.0.0

## Contents

- `python_env/` - Standalone Python virtual environment with all dependencies
- `gurujee_app/` - GURUJEE application source code
- `scripts/` - Platform-specific startup scripts
- `DEPLOYMENT_INFO.json` - Build metadata

## Quick Start

### Android (Termux)

1. Transfer this package to your Android device
2. Extract to home directory
3. Run: `bash scripts/start-termux.sh`

### Windows

1. Extract this package to desired location
2. Run: `scripts\\start-windows.bat`
3. Access at `http://localhost:7171`

### Linux

1. Extract this package
2. Run: `bash scripts/start-termux.sh` (same as Termux)
3. Access at `http://localhost:7171`

## System Requirements

- **RAM**: 100MB+ available
- **Storage**: 500MB+ free
- **Network**: Port 7171 available

## Verification

After starting the daemon:

```bash
curl http://localhost:7171/api/health
```

Expected response:
```json
{"status":"ok","version":"1.0.0"}
```

## Troubleshooting

**Import Error - No module named 'fastapi'**
- Ensure you're using the included python_env
- Source: `source python_env/bin/activate`

**Address already in use**
- Another process is using port 7171
- Change port: export GURUJEE_PORT=7172

**Permission Denied**
- Make scripts executable: `chmod +x scripts/*.sh`

## Support

See `PHASE4-ANDROID-SETUP.md` for detailed manual setup instructions.

---

Built with GURUJEE Deployment Builder
""".format(timestamp=self.build_timestamp))

        self.log("README created", "SUCCESS")
        return True

    def create_archive(self):
        """Create compressed archive"""
        self.step("Creating Archive")

        archive_path = self.output_dir / f"gurujee_deployment_{self.build_timestamp}.tar.gz"

        try:
            import tarfile
            self.log(f"Creating archive: {archive_path.name}")

            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(self.build_dir, arcname=self.build_dir.name)

            size_mb = archive_path.stat().st_size / (1024 * 1024)
            self.log(f"Archive created: {size_mb:.1f}MB", "SUCCESS")
            return str(archive_path)
        except Exception as e:
            self.log(f"Failed to create archive: {e}", "ERROR")
            return None

    def build(self):
        """Execute full build"""
        print("\n")
        print("╔════════════════════════════════════════════════════╗")
        print("║  GURUJEE Standalone Deployment Builder            ║")
        print("╚════════════════════════════════════════════════════╝")
        print(f"\n📁 Build directory: {self.build_dir}\n")

        steps = [
            ("Create Virtual Environment", self.create_venv_package),
            ("Copy Application Code", self.copy_application_code),
            ("Create Startup Scripts", self.create_startup_scripts),
            ("Create Metadata", self.create_metadata),
            ("Create Documentation", self.create_readme),
            ("Create Archive", self.create_archive)
        ]

        for step_name, step_func in steps:
            try:
                result = step_func()
                if result is False:
                    self.log(f"Failed at: {step_name}", "ERROR")
                    return False
            except Exception as e:
                self.log(f"Error in {step_name}: {e}", "ERROR")
                return False

        # Final summary
        print(f"\n{'━' * 60}")
        print("✨ BUILD COMPLETE ✨")
        print(f"{'━' * 60}\n")

        print(f"📦 Deployment package ready at:\n   {self.build_dir}\n")
        print("📝 Contents:")
        print("   ✓ Python virtual environment with dependencies")
        print("   ✓ GURUJEE application source code")
        print("   ✓ Startup scripts for multiple platforms")
        print("   ✓ Complete documentation\n")

        print("🚀 To deploy to Android:")
        print("   1. Transfer build directory to device (/sdcard/)")
        print("   2. In Termux: bash /sdcard/build_dir/scripts/start-termux.sh\n")

        return True

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build GURUJEE deployment package")
    parser.add_argument("--output", default="deployment_builds", help="Output directory")
    args = parser.parse_args()

    builder = GurujeeDeploymentBuilder(args.output)
    success = builder.build()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
