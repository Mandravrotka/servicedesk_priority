#!/bin/bash
set -e

echo "Initializing JKH Priority AI..." >&2

if ! command -v docker &> /dev/null; then
    echo "Error: Docker not found" >&2
    exit 1
fi

if [ ! -f "../.env" ]; then
    if [ -f "../.env.example" ]; then
        cp ../.env.example ../.env
        echo "Created .env from .env.example" >&2
        echo "⚠️  Edit ../.env before continuing (replace host.docker.internal with 172.17.0.1 for Linux)" >&2
        read -p "Press Enter to continue..."
    else
        echo "Error: No .env or .env.example found" >&2
        exit 1
    fi
fi

cd ..
docker-compose up -d
sleep 8

cd setup
./import-credentials.sh
./import-workflow.sh "" "../workflow/jkh-priority-workflow.json"
./import-workflow.sh "" "../workflow/telegram-listener.json"
cd ..

echo "" >&2
echo "✓ Done! Open http://localhost:5678 and activate both workflows" >&2