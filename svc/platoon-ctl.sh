#!/bin/bash

# Sets PYTHONPATH to siqhashlib if running FIPS enabled
source ${BINPATH}/fips_python

case "$1" in
  start)
    ${ENVPATH}/python/bin/bake -m spire.tasks spire.daemon config=${SVCPATH}/platoon/platoon.yaml
    ;;
  stop)
    if [[ -e ${VARPATH}/platoon.pid ]]; then
      /bin/bash -c '/bin/kill $(<${VARPATH}/platoon.pid)'
    fi
    ;;
esac
