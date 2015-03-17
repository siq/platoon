#!/bin/sh
if [ "$1" -eq 0 ]; then
  "${BINPATH}/invoke-monit" -q stop platoon
fi
