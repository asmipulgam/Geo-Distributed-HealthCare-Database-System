#!/bin/bash
# Run CockroachDB binary locally on a specified port.
# Usage: ./run_cockroach_binary.sh [PORT]

PORT=${1:-26257}
DATA_DIR="cockroach-data-${PORT}"

echo "🚀 Starting local CockroachDB node on port ${PORT}..."
echo "📁 Data directory: ${DATA_DIR}"

mkdir -p ${DATA_DIR}

./cockroach start-single-node \
  --insecure \
  --store=${DATA_DIR} \
  --listen-addr=localhost:${PORT} \
  --http-addr=localhost:$((PORT + 1))

if [ $? -eq 0 ]; then
  echo "✅ CockroachDB started successfully."
  echo "🗄️  SQL Port: ${PORT}"
  echo "🌐 Web UI: http://localhost:$((PORT + 1))"
else
  echo "❌ Failed to start CockroachDB binary."
fi
