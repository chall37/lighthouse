#!/usr/bin/env python3
"""
Run all CI checks locally before pushing.
Mirrors the CI workflow in .gitea/workflows/ci.yml
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import Tuple

# Colors for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

# Track results
passed_checks = []
failed_checks = []


def print_header(text: str) -> None:
    """Print a section header."""
    print(f"{BLUE}{'=' * 40}{NC}")
    print(f"{BLUE}{text}{NC}")
    print(f"{BLUE}{'=' * 40}{NC}")


def print_step(text: str) -> None:
    """Print a step description."""
    print(f"\n{YELLOW}▶ {text}{NC}")


def run_command(cmd: list[str], check_name: str, log_file: Path) -> bool:
    """
    Run a command and capture output to log file.

    Returns True if successful, False otherwise.
    """
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False
            )
            f.write(result.stdout)

            # Also print to console
            print(result.stdout, end='')

            if result.returncode == 0:
                passed_checks.append(check_name)
                print(f"{GREEN}✓ {check_name} passed{NC}")
                return True
            else:
                failed_checks.append(check_name)
                print(f"{RED}✗ {check_name} failed{NC}")
                return False
    except Exception as e:
        failed_checks.append(check_name)
        print(f"{RED}✗ {check_name} failed: {e}{NC}")
        return False


def main() -> int:
    """Run all CI checks."""
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Create logs directory
    logs_dir = project_root / ".ci-logs"
    logs_dir.mkdir(exist_ok=True)

    # Change to project root
    import os
    os.chdir(project_root)

    start_time = time.time()

    print_header("Lighthouse Local CI Checks")
    print("Running all CI checks locally...\n")

    # ==========================================
    # Test Job
    # ==========================================
    print_header("Test Job (Python 3.12)")

    print_step("Running tests with pytest")
    run_command(
        [sys.executable, "-m", "pytest", "-v", "--tb=short"],
        "pytest",
        logs_dir / "pytest.log"
    )

    print_step("Running type checking with mypy")
    run_command(
        [sys.executable, "-m", "mypy", "lighthouse/", "--ignore-missing-imports"],
        "mypy",
        logs_dir / "mypy.log"
    )

    print_step("Building wheel")
    # Install build first (silently)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "build"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False
    )
    run_command(
        [sys.executable, "-m", "build", "--wheel"],
        "build",
        logs_dir / "build.log"
    )

    # ==========================================
    # Lint Job
    # ==========================================
    print_header("Code Quality & Linting")

    print_step("Running Ruff linter")
    run_command(
        [sys.executable, "-m", "ruff", "check", "lighthouse/", "tests/"],
        "ruff",
        logs_dir / "ruff.log"
    )

    print_step("Running Pylint")
    run_command(
        [
            sys.executable, "-m", "pylint", "lighthouse/",
            "--disable=C0114,C0115,C0116,R0903,W0511,W0613,W0718,W0212",
            "--max-line-length=100",
            "--fail-under=9.0"
        ],
        "pylint",
        logs_dir / "pylint.log"
    )

    print_step("Checking code complexity with Radon")
    # Run both radon commands
    success = True
    with open(logs_dir / "radon.log", 'w', encoding='utf-8') as f:
        for cmd in [
            [sys.executable, "-m", "radon", "cc", "lighthouse/", "-a", "-nb"],
            [sys.executable, "-m", "radon", "mi", "lighthouse/", "-nb"]
        ]:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False
            )
            f.write(result.stdout)
            print(result.stdout, end='')
            if result.returncode != 0:
                success = False

    if success:
        passed_checks.append("radon")
        print(f"{GREEN}✓ radon passed{NC}")
    else:
        failed_checks.append("radon")
        print(f"{RED}✗ radon failed{NC}")

    # ==========================================
    # Security Job
    # ==========================================
    print_header("Security Analysis")

    print_step("Running Bandit security scanner")
    run_command(
        [sys.executable, "-m", "bandit", "-r", "lighthouse/", "--severity-level", "medium"],
        "bandit",
        logs_dir / "bandit.log"
    )

    print_step("Checking dependencies for vulnerabilities with pip-audit")
    # Build ignore flags
    ignore_flags = []
    ignore_file = project_root / ".pip-audit-ignores.txt"
    if ignore_file.exists():
        with open(ignore_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    ignore_flags.extend(["--ignore-vuln", line])

    run_command(
        [sys.executable, "-m", "pip_audit", "--skip-editable"] + ignore_flags,
        "pip-audit",
        logs_dir / "pip-audit.log"
    )

    # ==========================================
    # Summary
    # ==========================================
    duration = int(time.time() - start_time)

    print()
    print_header("Summary")

    print(f"\n{GREEN}Passed Checks ({len(passed_checks)}):{NC}")
    for check in passed_checks:
        print(f"  {GREEN}✓{NC} {check}")

    if failed_checks:
        print(f"\n{RED}Failed Checks ({len(failed_checks)}):{NC}")
        for check in failed_checks:
            print(f"  {RED}✗{NC} {check}")

    print(f"\n{BLUE}Duration:{NC} {duration}s")

    # Exit with error if any checks failed
    if failed_checks:
        print(f"\n{RED}❌ Some checks failed. Please fix the issues before pushing.{NC}")
        print(f"\nCheck the log files in {logs_dir}/ for details:")
        for log_file in sorted(logs_dir.glob("*.log")):
            print(f"  - {log_file}")
        return 1
    else:
        print(f"\n{GREEN}✅ All checks passed! Safe to push.{NC}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
