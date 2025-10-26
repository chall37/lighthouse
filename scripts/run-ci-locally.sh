#!/bin/bash
# Run all CI checks locally before pushing
# Mirrors the CI workflow in .gitea/workflows/ci.yml

set -e  # Exit on first error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Create logs directory
LOGS_DIR="$PROJECT_ROOT/.ci-logs"
mkdir -p "$LOGS_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track failures
FAILED_CHECKS=()
PASSED_CHECKS=()

# Print header
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Print step
print_step() {
    echo -e "\n${YELLOW}▶ $1${NC}"
}

# Record result
record_result() {
    if [ $1 -eq 0 ]; then
        PASSED_CHECKS+=("$2")
        echo -e "${GREEN}✓ $2 passed${NC}"
    else
        FAILED_CHECKS+=("$2")
        echo -e "${RED}✗ $2 failed${NC}"
    fi
}

# Start timer
START_TIME=$(date +%s)

print_header "Lighthouse Local CI Checks"
echo "Running all CI checks locally..."
echo

# ==========================================
# Test Job
# ==========================================
print_header "Test Job (Python 3.12)"

print_step "Running tests with pytest"
if python -m pytest -v --tb=short 2>&1 | tee /tmp/pytest-output.txt; then
    record_result 0 "pytest"
else
    record_result 1 "pytest"
fi

print_step "Running type checking with mypy"
if python -m mypy lighthouse/ --ignore-missing-imports 2>&1 | tee /tmp/mypy-output.txt; then
    record_result 0 "mypy"
else
    record_result 1 "mypy"
fi

print_step "Building wheel"
if python -m pip install build > /dev/null 2>&1 && \
   python -m build --wheel 2>&1 | tee /tmp/build-output.txt; then
    record_result 0 "build"
else
    record_result 1 "build"
fi

# ==========================================
# Lint Job
# ==========================================
print_header "Code Quality & Linting"

print_step "Running Ruff linter"
if python -m ruff check lighthouse/ tests/ 2>&1 | tee /tmp/ruff-output.txt; then
    record_result 0 "ruff"
else
    record_result 1 "ruff"
fi

print_step "Running Pylint"
if python -m pylint lighthouse/ --disable=C0114,C0115,C0116,R0903,W0511,W0613,W0718,W0212 --max-line-length=100 --fail-under=9.0 2>&1 | tee /tmp/pylint-output.txt; then
    record_result 0 "pylint"
else
    record_result 1 "pylint"
fi

print_step "Checking code complexity with Radon"
if radon cc lighthouse/ -a -nb 2>&1 | tee /tmp/radon-cc-output.txt && \
   radon mi lighthouse/ -nb 2>&1 | tee /tmp/radon-mi-output.txt; then
    record_result 0 "radon"
else
    record_result 1 "radon"
fi

# ==========================================
# Security Job
# ==========================================
print_header "Security Analysis"

print_step "Running Bandit security scanner"
if bandit -r lighthouse/ --severity-level medium 2>&1 | tee /tmp/bandit-output.txt; then
    record_result 0 "bandit"
else
    record_result 1 "bandit"
fi

print_step "Checking dependencies for vulnerabilities with pip-audit"
if [ -f ".pip-audit-ignores.txt" ]; then
    IGNORE_FLAGS=$(grep -v '^#' .pip-audit-ignores.txt | grep -v '^$' | sed 's/^/--ignore-vuln /' | tr '\n' ' ')
else
    IGNORE_FLAGS=""
fi

if pip-audit --skip-editable $IGNORE_FLAGS 2>&1 | tee /tmp/pip-audit-output.txt; then
    record_result 0 "pip-audit"
else
    record_result 1 "pip-audit"
fi

# ==========================================
# Summary
# ==========================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo
print_header "Summary"

echo -e "\n${GREEN}Passed Checks (${#PASSED_CHECKS[@]}):${NC}"
for check in "${PASSED_CHECKS[@]}"; do
    echo -e "  ${GREEN}✓${NC} $check"
done

if [ ${#FAILED_CHECKS[@]} -gt 0 ]; then
    echo -e "\n${RED}Failed Checks (${#FAILED_CHECKS[@]}):${NC}"
    for check in "${FAILED_CHECKS[@]}"; do
        echo -e "  ${RED}✗${NC} $check"
    done
fi

echo -e "\n${BLUE}Duration:${NC} ${DURATION}s"

# Exit with error if any checks failed
if [ ${#FAILED_CHECKS[@]} -gt 0 ]; then
    echo -e "\n${RED}❌ Some checks failed. Please fix the issues before pushing.${NC}"
    echo -e "\nCheck the log files in /tmp/ for details:"
    echo "  - /tmp/pytest-output.txt"
    echo "  - /tmp/mypy-output.txt"
    echo "  - /tmp/build-output.txt"
    echo "  - /tmp/ruff-output.txt"
    echo "  - /tmp/pylint-output.txt"
    echo "  - /tmp/radon-cc-output.txt"
    echo "  - /tmp/radon-mi-output.txt"
    echo "  - /tmp/bandit-output.txt"
    echo "  - /tmp/pip-audit-output.txt"
    exit 1
else
    echo -e "\n${GREEN}✅ All checks passed! Safe to push.${NC}"
    exit 0
fi
