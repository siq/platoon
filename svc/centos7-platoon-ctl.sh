#!/bin/bash

# Sets PYTHONPATH to siqhashlib if running FIPS enabled
source /siq/bin/fips_python

case "$1" in
  start)
    /siq/bin/bake -m spire.tasks spire.daemon config=/siq/svc/platoon/platoon.yaml
    ;;
  stop)
    if [[ -e /var/siq/run/platoon.pid ]]; then
      /bin/bash -c '/bin/kill $(</var/siq/run/platoon.pid)'
    fi
    ;;
esac
