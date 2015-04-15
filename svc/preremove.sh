#!/bin/sh
if [ "$1" -eq 0 ]; then
  "${SVCPATH}/platoon/platoon-ctl" stop
fi
