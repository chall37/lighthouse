#!/bin/bash
# Comprehensive CI diagnostics script

# Get token from .gitea-token file if it exists, otherwise use default
if [ -f "$(dirname "$0")/../.gitea-token" ]; then
  GITEA_TOKEN=$(cat "$(dirname "$0")/../.gitea-token")
else
  GITEA_TOKEN="${GITEA_TOKEN:-a46c33dbc2d1220e3db0e831d7aa93a1cb74bdc9}"
fi

REPO="hall/lighthouse"
GITEA_URL="https://gitea.notyourz.org"
SERVER="hall@192.168.10.101"

echo "========================================="
echo "Lighthouse CI Diagnostics"
echo "========================================="
echo

# Check if server is reachable
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes $SERVER "echo 'connected'" >/dev/null 2>&1; then
  echo "✗ Error: Cannot reach server $SERVER"
  echo "  Please check network connection and SSH access"
  exit 1
fi

# Get latest commit
COMMIT=$(curl -s --max-time 10 -H "Authorization: token $GITEA_TOKEN" \
  "$GITEA_URL/api/v1/repos/$REPO/commits?limit=1" | \
  python3 -c "import sys, json; data = sys.stdin.read(); print(json.loads(data)[0]['sha'][:7] if data else 'unknown')" 2>/dev/null)

if [ -z "$COMMIT" ] || [ "$COMMIT" = "unknown" ]; then
  echo "✗ Error: Cannot fetch commit information from $GITEA_URL"
  echo "  Server may be unreachable or API token may be invalid"
  exit 1
fi

echo "Commit: $COMMIT"
echo

# Get workflow runs for this commit
echo "=== Workflow Runs for Latest Commit ==="
curl -s --max-time 10 -H "Authorization: token $GITEA_TOKEN" \
  "$GITEA_URL/api/v1/repos/$REPO/actions/tasks" | \
  python3 -c "
import sys, json
from datetime import datetime

try:
    raw_data = sys.stdin.read()
    if not raw_data:
        print('No data received from API')
        sys.exit(0)
    data = json.loads(raw_data)
except json.JSONDecodeError:
    print('Error: Invalid JSON response from API')
    sys.exit(0)
runs = data.get('workflow_runs', [])

# Filter runs for the commit we're looking at
commit_sha = '$COMMIT'
commit_runs = [r for r in runs if r['head_sha'].startswith(commit_sha)]

if not commit_runs:
    print('No workflow runs found for this commit')
    sys.exit(0)

# Group by job name and show status
jobs = {}
for run in commit_runs:
    name = run['name']
    if name not in jobs:
        jobs[name] = run

# Determine overall status
statuses = [j['status'] for j in jobs.values()]
if all(s == 'success' for s in statuses):
    overall = 'SUCCESS'
elif any(s == 'failure' for s in statuses):
    overall = 'FAILURE'
elif any(s in ['pending', 'running'] for s in statuses):
    overall = 'RUNNING'
else:
    overall = 'UNKNOWN'

print(f'Overall: {overall}')
print()

for name, run in sorted(jobs.items()):
    status = run['status']
    icon = '✓' if status == 'success' else '✗' if status == 'failure' else '⏳'

    # Calculate duration
    started = datetime.fromisoformat(run['run_started_at'].replace('Z', '+00:00'))
    updated = datetime.fromisoformat(run['updated_at'].replace('Z', '+00:00'))
    duration = int((updated - started).total_seconds())

    print(f'{icon} {name}')
    print(f'  Status: {status}')
    print(f'  Duration: {duration}s')
    print(f'  Run ID: {run[\"id\"]}')
    print(f'  URL: {run[\"url\"]}')
    print()
"

# Check runner status
echo "=== Runner Status ==="
echo -n "Container: "
ssh $SERVER "docker ps -f name=gitea-runner --format '{{.Status}}'"
echo

echo -n "Labels: "
ssh $SERVER "docker logs gitea-runner 2>&1" | grep "with labels:" | tail -1 | sed 's/.*with labels: //'
echo

# Check for runner errors
echo "=== Runner Error Analysis ==="
RUNNER_ERRORS=$(ssh $SERVER "docker logs gitea-runner 2>&1" | grep -iE "error|failed|denied|cannot connect|not found|unauthorized|unhealthy|version '.*' was not found|::error::")

if [ -z "$RUNNER_ERRORS" ]; then
  echo "✓ No critical errors found in runner logs."
else
  echo "✗ Found potential errors in runner logs:"
  echo "$RUNNER_ERRORS" | tail -15
fi
echo

# Check Gitea logs for action errors
echo "=== Gitea Action Logs ==="
ssh $SERVER "docker logs --tail 100 gitea 2>&1" | grep -iE "action|workflow" | grep -iE "error|warn|fail|no matching" | tail -10
echo

# Show recent workflow history
echo "=== Recent Workflow History (Last 5 runs) ==="
curl -s --max-time 10 -H "Authorization: token $GITEA_TOKEN" \
  "$GITEA_URL/api/v1/repos/$REPO/actions/tasks" | \
  python3 -c "
import sys, json
from datetime import datetime

try:
    raw_data = sys.stdin.read()
    if not raw_data:
        print('No data received from API')
        sys.exit(0)
    data = json.loads(raw_data)
except json.JSONDecodeError:
    print('Error: Invalid JSON response from API')
    sys.exit(0)
runs = data.get('workflow_runs', [])

# Get unique runs by run_number, take latest 5
seen = set()
unique_runs = []
for run in runs:
    run_num = run['run_number']
    if run_num not in seen:
        seen.add(run_num)
        unique_runs.append(run)
        if len(unique_runs) >= 5:
            break

for run in unique_runs:
    status = run['status']
    icon = '✓' if status == 'success' else '✗' if status == 'failure' else '⏳'
    sha = run['head_sha'][:7]

    print(f'{icon} Run #{run[\"run_number\"]}: {run[\"display_title\"]} ({sha})')
    print(f'  Status: {status}')
"
echo

# Summary
echo "========================================="
echo "To view full logs:"
echo "  Web UI: $GITEA_URL/$REPO/actions"
echo "  Runner: ssh $SERVER 'docker logs -f gitea-runner'"
echo "  Gitea:  ssh $SERVER 'docker logs -f gitea'"
echo
echo "Note: Job logs API not available in Gitea 1.24.6"
echo "      View detailed logs in Web UI until API support is added"
echo "========================================="
