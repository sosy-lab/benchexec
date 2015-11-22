#!/bin/sh
# Only report test coverage to codacy for one of the builds (with Python 3.4)
if [ ! -z "$CODACY_PROJECT_TOKEN" ] && \
    python -c 'import sys; sys.exit(0 if sys.version_info[0:2] == (3,4) else 1)'; then
  python-codacy-coverage -r coverage.xml
fi
