#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${EGM_PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    printf '%s\n' 'Python 3.10+ is required. Install it or set EGM_PYTHON.' >&2
    exit 1
fi

if ! "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
    printf '%s\n' 'Python 3.10+ is required.' >&2
    exit 1
fi

export PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON" -m egm_copilot install "$@"