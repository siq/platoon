#!/bin/bash
(
set -x
# Sets PYTHONPATH to siqhashlib if running FIPS enabled
source /siq/bin/fips_python
timeout=300

case "$1" in
  start)
    while (( $timeout > 0 )); do
      [[ -e /var/siq/run/nucleus-services-ready ]] && break
      #[[ -e /var/siq/run/nucleus-services-ready && $(nc -z 127.0.0.1 80) ]] && break
      sleep 1
      let timeout--
    done
    [[ $timeout == 0 ]] && exit 1
    sleep 3
    /siq/env/python/bin/bake -m spire.tasks spire.daemon config=/siq/svc/platoon/platoon.yaml
    ;;
  stop)
    if [[ -e /var/siq/run/platoon.pid ]]; then
      /bin/bash -c '/bin/kill $(</var/siq/run/platoon.pid)'
    fi
    ;;
esac
) > /var/siq/log/platoon-script.log 2>&1 &
