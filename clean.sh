#!/usr/bin/env bash
#
# Clean up build artifacts from the Python build and setuptools modules
#
ME=$(basename "$0")
MYDIR=$(cd "$(dirname "$0")" && pwd)

cd "$MYDIR" || exit 1  # do or do not, there is no try
rm -r build/ dist/ *.egg-info  2> /dev/null
find . -type d -name '__pycache__' -print0 | xargs -0 rm -r
