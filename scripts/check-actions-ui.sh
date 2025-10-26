#!/bin/bash
# Script to check Actions status via Web UI scraping

GITEA_TOKEN="a46c33dbc2d1220e3db0e831d7aa93a1cb74bdc9"
GITEA_URL="https://gitea.notyourz.org"
REPO="hall/lighthouse"

echo "========================================="
echo "Checking Actions UI for Errors"
echo "========================================="
echo

# Get the actions page HTML and look for error messages
echo "Fetching Actions page..."
ACTIONS_HTML=$(curl -s -H "Authorization: token $GITEA_TOKEN" "$GITEA_URL/$REPO/actions")

# Look for common error patterns
echo "Error Messages Found:"
echo "$ACTIONS_HTML" | grep -oE '<div class="[^"]*error[^"]*"[^>]*>.*?</div>' | sed 's/<[^>]*>//g' | head -10

echo
echo "Looking for 'no matching' messages..."
echo "$ACTIONS_HTML" | grep -i "no matching" | sed 's/<[^>]*>//g' | head -5

echo
echo "Looking for workflow run statuses..."
echo "$ACTIONS_HTML" | grep -iE "waiting|pending|running|failed|success" | sed 's/<[^>]*>//g' | grep -v "^$" | head -10

echo
echo "========================================="
