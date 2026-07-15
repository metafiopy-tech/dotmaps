#!/usr/bin/env bash
# Dot 001: the build produced a deployable artifact. Mechanical, seconds.
# The traveler's job is to run the build; this verifier only checks its output.
set -u
WS=""
while [ $# -gt 0 ]; do case "$1" in --workspace) WS="$2"; shift 2;; *) shift;; esac; done
found=""
for d in "$WS/dist" "$WS/.output" "$WS/build" "$WS/.vercel/output"; do
  if [ -d "$d" ] && [ -n "$(ls -A "$d" 2>/dev/null)" ]; then found="$d"; break; fi
done
if [ -n "$found" ]; then
  echo "{\"dot\":\"001\",\"pass\":true,\"evidence\":\"build artifact present at ${found##*/}\"}"
  exit 0
else
  echo "{\"dot\":\"001\",\"pass\":false,\"evidence\":\"no build artifact (dist/.output/build) in workspace\"}"
  exit 1
fi
