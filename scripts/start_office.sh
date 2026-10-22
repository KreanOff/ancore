#!/bin/sh
# Compatibility shortcut; the local ONLYOFFICE launcher lives in scripts/office/.
set -eu
ANCORE_ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd -P)
exec sh "$ANCORE_ROOT/scripts/office/start.sh" "$@"
