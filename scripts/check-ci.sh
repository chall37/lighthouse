#!/bin/bash
# Script to check CI status via Gitea API

GITEA_TOKEN="${GITEA_TOKEN:-a46c33dbc2d1220e3db0e831d7aa93a1cb74bdc9}"
REPO="hall/lighthouse"
GITEA_URL="https://gitea.notyourz.org"

# Get latest commit
COMMIT=$(curl -s -H "Authorization: token $GITEA_TOKEN" \
  "$GITEA_URL/api/v1/repos/$REPO/commits?limit=1" | \
  python -c "import sys, json; print(json.load(sys.stdin)[0]['sha'][:7])")

echo "Checking CI status for commit: $COMMIT"
echo "========================================="

# Get commit status
curl -s -H "Authorization: token $GITEA_TOKEN" \
  "$GITEA_URL/api/v1/repos/$REPO/commits/$COMMIT/status" | \
  python3 -c '
import sys, json
data = json.load(sys.stdin)
print("Overall State:", data["state"].upper())
print("Total Checks:", data["total_count"])
print()
for status in data["statuses"]:
    symbol = "✓" if status["status"] == "success" else "✗" if status["status"] == "failure" else "⏳"
    print(symbol, status["context"])
    print("  Status:", status["status"])
    print("  Description:", status["description"])
    print("  URL:", data["repository"]["html_url"] + status["target_url"])
    print()
'

echo "========================================="
echo "Full Actions URL: $GITEA_URL/$REPO/actions"
