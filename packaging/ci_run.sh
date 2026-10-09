#!/usr/bin/env bash
# Runs one build command in CI. When it fails, the last lines of its output are
# posted as an error on the run page (the full log may not be reachable).
#   packaging/ci_run.sh "<title>" command args...
title=$1; shift
log=$(mktemp)
"$@" 2>&1 | tee "$log"
status=${PIPESTATUS[0]}
if [ "$status" -ne 0 ]; then
  tail -n 40 "$log" | sed ':a;N;$!ba;s/%/%25/g;s/\r//g;s/\n/%0A/g' | { read -r -d '' text; echo "::error title=$title (exit $status)::$text"; }
fi
rm -f "$log"
exit "$status"
