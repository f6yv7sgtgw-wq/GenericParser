#!/usr/bin/env sh
set -eu
python -m pip install -e .
exec generic-parser-web
