#!/bin/sh

HOST=$1
PORT=$2
POST_SUCCESS_WAIT=${3:-0}

is_non_negative_int() {
  case $1 in
    ''|*[!0-9]*) return 1 ;;
    *) return 0 ;;
  esac
}

if [ -z "$HOST" ] || [ -z "$PORT" ]; then
  echo "Please specify a host and port, e.g. localhost 80"
  exit 1
fi

if [ -z "$CHECK_FREQUENCY" ]; then
  echo "CHECK_FREQUENCY is empty, exiting"
  exit 1
fi

if [ -z "$MAX_WAIT_SECONDS" ]; then
  echo "MAX_WAIT_SECONDS is empty, exiting"
  exit 1
fi

if ! is_non_negative_int "$MAX_WAIT_SECONDS" || [ "$MAX_WAIT_SECONDS" -eq 0 ]; then
  echo "MAX_WAIT_SECONDS must be a positive integer, exiting"
  exit 1
fi

if ! is_non_negative_int "$POST_SUCCESS_WAIT"; then
  echo "POST_SUCCESS_WAIT must be a non-negative integer, exiting"
  exit 1
fi

echo "Waiting for $HOST:$PORT (timeout $MAX_WAIT_SECONDS seconds)..."
START_TIME=$(date +%s)

while true; do
  if nc -z "$HOST" "$PORT"; then
    if [ "$POST_SUCCESS_WAIT" -gt 0 ] 2>/dev/null; then
      echo "Port is open, waiting an extra $POST_SUCCESS_WAIT seconds..."
      sleep "$POST_SUCCESS_WAIT"
    fi
    echo "OK"
    exit 0
  fi

  CURRENT_TIME=$(date +%s)
  ELAPSED=$((CURRENT_TIME - START_TIME))
  if [ "$ELAPSED" -ge "$MAX_WAIT_SECONDS" ]; then
    echo "Timed out after $MAX_WAIT_SECONDS seconds waiting for $HOST:$PORT"
    exit 1
  fi

  sleep "$CHECK_FREQUENCY"
done
