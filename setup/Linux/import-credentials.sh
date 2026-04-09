#!/bin/bash
set -e

CONTAINER_NAME="${1:-n8n}"
CREDENTIALS_FILE="${2:-../credentials/ollama-credentials.json}"

if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo "Error: Credentials file not found: $CREDENTIALS_FILE" >&2
    exit 1
fi

docker cp "$CREDENTIALS_FILE" "$CONTAINER_NAME:/tmp/import-credentials.json"
if [ $? -ne 0 ]; then
    echo "Error: Failed to copy credentials to container" >&2
    exit 1
fi

docker exec "$CONTAINER_NAME" n8n import:credentials --input /tmp/import-credentials.json
if [ $? -ne 0 ]; then
    echo "Error: Failed to import credentials" >&2
    exit 1
fi


echo "✓ Credentials imported" >&2