#!/usr/bin/env bash
set -euo pipefail
VERSION_ID="${1:-}"
if [[ -n "$VERSION_ID" ]]; then
  npx wrangler rollback "$VERSION_ID" --name generic-parser-mobile --message "Manual rollback GenericParser 0.2d"
else
  npx wrangler rollback --name generic-parser-mobile --message "Manual rollback GenericParser 0.2d"
fi
