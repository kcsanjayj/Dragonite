"""
run_agent.py

Single-file launcher for the existing Autonomous AI Agent project.

Run from the project root:

    python run_agent.py

This file does NOT replace the existing architecture.
It simply starts the existing CLI through one command.
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# START APPLICATION
# ============================================================

def main() -> None:
    print("=" * 70)
    print("AUTONOMOUS AI AGENT")
    print("=" * 70)
    print(f"Project: {PROJECT_ROOT}")
    print()

    # --------------------------------------------------------
    # Load existing CLI
    # --------------------------------------------------------

    try:
        from multi_tool_agent.cli import main as cli_main

    except Exception as exc:
        print("=" * 70)
        print("FAILED TO LOAD AUTONOMOUS AI AGENT")
        print("=" * 70)
        print(f"Error: {exc}")
        print()

        traceback.print_exc()

        print()
        print("=" * 70)
        print("CHECK:")
        print("=" * 70)
        print("1. You are running from the project root.")
        print("2. The virtual environment is activated.")
        print("3. multi_tool_agent/ exists.")
        print("4. multi_tool_agent/cli.py exists.")
        print("5. The existing project files are intact.")
        print()

        raise SystemExit(1)

    # --------------------------------------------------------
    # Start existing CLI
    # --------------------------------------------------------

    try:
        cli_main()

    except KeyboardInterrupt:
        print()
        print("=" * 70)
        print("AGENT STOPPED BY USER")
        print("=" * 70)

    except Exception as exc:
        print()
        print("=" * 70)
        print("AGENT ERROR")
        print("=" * 70)
        print(exc)
        print()

        traceback.print_exc()

        raise SystemExit(1)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()