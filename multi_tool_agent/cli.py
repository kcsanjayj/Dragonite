from __future__ import annotations

import sys

from multi_tool_agent.runtime.engine import AutonomousEngine


def main() -> None:
    print("=" * 70)
    print("AUTONOMOUS AI AGENT")
    print("Type 'exit' or 'quit' to stop.")
    print("=" * 70)

    engine = AutonomousEngine(max_cycles=5)

    while True:
        try:
            user_request = input("\nYou: ").strip()

        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if not user_request:
            continue

        if user_request.lower() in {"exit", "quit"}:
            print("Exiting.")
            break

        print("\nAgent is working...\n")

        try:
            result = engine.run(user_request)

            print("\n" + "=" * 70)
            print("FINAL ANSWER")
            print("=" * 70)

            print(result.get("answer", ""))

            print("\n" + "-" * 70)
            print("RUN STATUS")
            print("-" * 70)

            print("SUCCESS:", result.get("success"))
            print("RUN ID:", result.get("run_id"))
            print("PROGRESS:", result.get("progress"))

        except Exception as exc:
            print("\n" + "=" * 70)
            print("AGENT ERROR")
            print("=" * 70)
            print(exc)


if __name__ == "__main__":
    main()