#!/bin/bash
# Script to check Gitea Actions runner status and errors

SERVER="hall@192.168.10.101"
RUNNER_CONTAINER="gitea-runner"

echo "========================================="
echo "Gitea Actions Runner Status"
echo "========================================="
echo

# Check if runner container is running
echo "Container Status:"
ssh $SERVER "docker ps -f name=$RUNNER_CONTAINER --format 'table {{.Names}}\t{{.Status}}\t{{.State}}'"
echo

# Get runner registration info
echo "Runner Registration:"
ssh $SERVER "docker logs $RUNNER_CONTAINER 2>&1 | grep -E 'Registering|registered|declare'" | head -5
echo

# Check for errors in runner
echo "Runner Errors/Warnings:"
ssh $SERVER "docker logs --tail 100 $RUNNER_CONTAINER 2>&1 | grep -iE 'error|warn|fail|no matching|level=error|level=warn'" | tail -10
echo

# Check Gitea logs for action-related errors
echo "Gitea Action Errors:"
ssh $SERVER "docker logs --tail 200 gitea 2>&1 | grep -iE 'action.*error|no matching|runner.*fail'" | tail -10
echo

# Check for task activity
echo "Task Activity:"
ssh $SERVER "docker logs --tail 50 $RUNNER_CONTAINER 2>&1 | grep -E 'task [0-9]|job|workflow'" | tail -10
echo

# Get last 20 lines of logs
echo "Last 20 Log Lines:"
ssh $SERVER "docker logs --tail 20 $RUNNER_CONTAINER 2>&1"
echo

echo "========================================="
echo "Runner Container: $RUNNER_CONTAINER on $SERVER"
echo "View full logs: ssh $SERVER 'docker logs -f $RUNNER_CONTAINER'"
echo "========================================="
