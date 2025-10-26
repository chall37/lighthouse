#!/usr/bin/env python3
"""Fix f-string logging to use lazy % formatting."""

import re
import sys
from pathlib import Path

def fix_fstring_logging(file_path: Path) -> int:
    """Fix f-string in logging calls."""
    content = file_path.read_text()
    original = content
    changes = 0

    # Pattern: logger.LEVEL(f"text {var} more")
    # Replace with: logger.LEVEL("text %s more", var)

    # Simple case: logger.method(f"text {single_var}")
    pattern = r'logger\.(debug|info|warning|error|critical)\(f"([^"]*?)\{([^}]+?)\}([^"]*?)"\)'

    def replace_single(match):
        nonlocal changes
        method = match.group(1)
        before = match.group(2)
        var = match.group(3)
        after = match.group(4)

        # Convert to % formatting
        msg = f'"{before}%s{after}"'
        changes += 1
        return f'logger.{method}({msg}, {var})'

    content = re.sub(pattern, replace_single, content)

    # Handle two variables: f"text {var1} middle {var2} end"
    pattern2 = r'logger\.(debug|info|warning|error|critical)\(f"([^"]*?)\{([^}]+?)\}([^"]*?)\{([^}]+?)\}([^"]*?)"\)'

    def replace_double(match):
        nonlocal changes
        method = match.group(1)
        before = match.group(2)
        var1 = match.group(3)
        middle = match.group(4)
        var2 = match.group(5)
        after = match.group(6)

        msg = f'"{before}%s{middle}%s{after}"'
        changes += 1
        return f'logger.{method}({msg}, {var1}, {var2})'

    content = re.sub(pattern2, replace_double, content)

    # Handle three variables
    pattern3 = r'logger\.(debug|info|warning|error|critical)\(f"([^"]*?)\{([^}]+?)\}([^"]*?)\{([^}]+?)\}([^"]*?)\{([^}]+?)\}([^"]*?)"\)'

    def replace_triple(match):
        nonlocal changes
        method = match.group(1)
        before = match.group(2)
        var1 = match.group(3)
        middle1 = match.group(4)
        var2 = match.group(5)
        middle2 = match.group(6)
        var3 = match.group(7)
        after = match.group(8)

        msg = f'"{before}%s{middle1}%s{middle2}%s{after}"'
        changes += 1
        return f'logger.{method}({msg}, {var1}, {var2}, {var3})'

    content = re.sub(pattern3, replace_triple, content)

    if content != original:
        file_path.write_text(content)
        print(f"Fixed {changes} f-strings in {file_path}")
        return changes
    return 0

def main():
    project_root = Path(__file__).parent.parent
    files = [
        "lighthouse/coordinator.py",
        "lighthouse/daemon.py",
        "lighthouse/notifiers.py",
        "lighthouse/state.py",
    ]

    total = 0
    for file in files:
        path = project_root / file
        if path.exists():
            total += fix_fstring_logging(path)

    print(f"\nTotal fixes: {total}")
    return 0 if total > 0 else 1

if __name__ == "__main__":
    sys.exit(main())
