#!/usr/bin/env python3
"""Generate secure API keys for webhook authentication."""

import argparse
import secrets
import sys
from pathlib import Path


def generate_api_key(length: int = 32) -> str:
    """
    Generate a cryptographically secure API key.

    Args:
        length: Length of the key in bytes (default: 32)

    Returns:
        Hex-encoded API key
    """
    return secrets.token_hex(length)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate secure API keys for Lighthouse webhook authentication"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="File to append the API key to (default: print to stdout)",
    )
    parser.add_argument(
        "--length",
        "-l",
        type=int,
        default=32,
        help="Length of key in bytes (default: 32, produces 64 hex chars)",
    )
    parser.add_argument(
        "--count",
        "-c",
        type=int,
        default=1,
        help="Number of keys to generate (default: 1)",
    )

    args = parser.parse_args()

    # Generate keys
    keys = [generate_api_key(args.length) for _ in range(args.count)]

    # Output
    if args.output:
        # Append to file
        try:
            with open(args.output, "a", encoding="utf-8") as f:
                for key in keys:
                    f.write(f"{key}\n")
            print(f"Added {len(keys)} API key(s) to {args.output}", file=sys.stderr)
            print(
                f"Key preview: {keys[0][:16]}...{keys[0][-16:]}", file=sys.stderr
            )
        except Exception as e:
            print(f"Error writing to file: {e}", file=sys.stderr)
            return 1
    else:
        # Print to stdout
        for key in keys:
            print(key)

    return 0


if __name__ == "__main__":
    sys.exit(main())
