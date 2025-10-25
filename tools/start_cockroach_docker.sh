#!/bin/bash
# Run CockroachDB inside Docker on a specified port.
# Usage: ./run_cockroach_docker.sh [PORT]

PORT=${1:-26257}

CONTAINER_NAME="cockroachdb_${PORT}"

echo "🚀 Starting CockroachDB Docker container on port ${PORT}..."

docker run -d \
  --name ${CONTAINER_NAME} \
  -p ${PORT}:26257 \
  -p 8080:8080 \
  cockroachdb/cockroach:v24.1.3 start-single-node \
  --insecure \
  --listen-addr=0.0.0.0:${PORT} \
  --http-addr=0.0.0.0:8080

if [ $? -eq 0 ]; then
  echo "✅ CockroachDB started successfully."
  echo "🗄️  SQL Port: ${PORT}"
  echo "🌐 Web UI: http://localhost:8080"
else
  echo "❌ Failed to start CockroachDB Docker instance."
fi
