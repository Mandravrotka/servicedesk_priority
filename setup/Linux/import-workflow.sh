#!/bin/bash
set -e

CONTAINER_NAME="${1:-n8n}"
WORKFLOW_FILE="${2:-../workflow/jkh-priority-workflow.json}"

if [ ! -f "$WORKFLOW_FILE" ]; then
    echo "Error: Workflow file not found: $WORKFLOW_FILE" >&2
    exit 1
fi

docker cp "$WORKFLOW_FILE" "$CONTAINER_NAME:/tmp/import-workflow.json"
if [ $? -ne 0 ]; then
    echo "Error: Failed to copy workflow to container" >&2
    exit 1
fi

docker exec "$CONTAINER_NAME" n8n import:workflow --input /tmp/import-workflow.json
if [ $? -ne 0 ]; then
    echo "Error: Failed to import workflow" >&2
    exit 1
fi

docker exec "$CONTAINER_NAME" rm /tmp/import-workflow.json

echo "✓ Workflow imported" >&2