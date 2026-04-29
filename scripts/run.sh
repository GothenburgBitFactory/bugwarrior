#!/bin/sh
# Run a command via `uv run` if uv is available, otherwise run it directly.
# If a .venv directory exists, prepend it to PATH so the venv's tools are
# used without requiring the user to have manually activated it.
if command -v uv >/dev/null 2>&1 && [ -f "uv.lock" ]; then
    exec uv run "$@"
else
    if [ -d ".venv" ]; then
        export PATH=".venv/bin:$PATH"
    fi
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "error: '$1' not found."
        echo "Make sure your virtualenv is set up (see CONTRIBUTING for instructions)."
        echo "To skip this hook: git commit --no-verify  (or -n)"
        echo "To skip only this hook: SKIP=$1 git commit"
        exit 1
    fi
    exec "$@"
fi
