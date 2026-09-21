#!/bin/sh
set -eu
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec "$ROOT/scripts/run_auto.sh"
