"""CLI entry point for GitHub Copilot device flow login."""

from __future__ import annotations

import asyncio
import sys

from .auth import CONFIG_DIR, TOKEN_FILE, device_flow_login, get_cached_access_token


def main() -> None:
    print()
    print("  GitHub Copilot Login for machine-core")
    print("  ======================================")
    print()
    print("  This will:")
    print("    1. Open your browser to https://github.com/login/device")
    print("    2. Display a code for you to enter on that page")
    print("    3. After you authorize, the OAuth token is saved to:")
    print(f"       {TOKEN_FILE}")
    print()

    existing = get_cached_access_token()
    if existing:
        print(f"  Note: You already have a cached token at {TOKEN_FILE}")
        answer = input("  Re-authenticate? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("  Aborted.")
            return

    try:
        token = asyncio.run(device_flow_login())
        print()
        print(f"  Login successful! Token saved to {TOKEN_FILE}")
        print("  The GitHub Copilot provider will now auto-load on Machine.start().")
        print()
    except KeyboardInterrupt:
        print("\n  Cancelled.")
        sys.exit(1)
    except TimeoutError:
        print("\n  Timed out waiting for authentication.")
        sys.exit(1)
    except Exception as e:
        print(f"\n  Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
