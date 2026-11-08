#!/usr/bin/env sh
# Linux/macOS: runs the Python installer. Same flags as install.py.
cd "$(dirname "$0")" && exec python3 install.py "$@"
