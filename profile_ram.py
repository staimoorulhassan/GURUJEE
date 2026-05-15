#!/usr/bin/env python3
"""
RAM profiling script for GURUJEE daemon idle footprint.
Measures: daemon startup → all agents initialized → idle listening state.
"""

import sys
import time
import psutil
import asyncio
from pathlib import Path
import os

# Add repo to path
sys.path.insert(0, str(Path(__file__).parent))

# Create test data directory and mock files
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

# Create minimal soul_identity.yaml if missing
soul_file = data_dir / "soul_identity.yaml"
if not soul_file.exists():
    soul_file.write_text("""name: GURUJEE
tagline: Your AI companion
personality_traits:
  - wise
  - concise
  - proactive
language_style: friendly
system_prompt_template: "You are {name}, {traits_joined}"
voice_id: null
""")

async def profile_daemon():
    """Start daemon and measure idle RAM footprint."""

    print("=" * 60)
    print("GURUJEE FOUNDATION - RAM PROFILING (T069)")
    print("=" * 60)
    print()

    # Get process handle
    process = psutil.Process()

    # Initial RSS before daemon starts
    initial_rss_mb = process.memory_info().rss / 1024 / 1024
    print(f"Initial process RSS: {initial_rss_mb:.2f} MB")

    # Import and start daemon
    print("\nStarting GatewayDaemon...")
    from gurujee.daemon.gateway_daemon import GatewayDaemon
    from gurujee.config.loader import ConfigLoader

    # Initialize config
    config_loader = ConfigLoader()

    # Create daemon (don't start server yet - measure agents only)
    daemon = GatewayDaemon()

    # Start all agents
    print("Initializing 6 agents (soul, memory, heartbeat, user_agent, cron, automation)...")
    start_time = time.time()

    try:
        # Start daemon task (this starts all agents)
        task = asyncio.create_task(daemon.start())

        # Wait for agents to initialize (~2 seconds)
        await asyncio.sleep(2)

        # Measure idle RSS after initialization
        idle_rss_mb = process.memory_info().rss / 1024 / 1024
        daemon_rss_mb = idle_rss_mb - initial_rss_mb

        init_time = time.time() - start_time

        print(f"[OK] Agents initialized in {init_time:.2f} seconds")
        print()
        print("=" * 60)
        print("IDLE STATE MEASUREMENT")
        print("=" * 60)
        print(f"Initial RSS:        {initial_rss_mb:8.2f} MB")
        print(f"Idle RSS:           {idle_rss_mb:8.2f} MB")
        print(f"Daemon overhead:    {daemon_rss_mb:8.2f} MB")
        print()

        if daemon_rss_mb <= 50:
            print(f"[PASS] {daemon_rss_mb:.2f} MB <= 50 MB (P1 constitutional requirement)")
            exit_code = 0
        else:
            print(f"[WARNING] {daemon_rss_mb:.2f} MB > 50 MB (P1 ceiling exceeded)")
            exit_code = 1

        print("=" * 60)

        # Cleanup
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        return exit_code

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(profile_daemon())
    sys.exit(exit_code)
