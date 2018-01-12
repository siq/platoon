#!/bin/sh
logreopen=${VARPATH}/platoonapi.logreopen
if [ ! -e "$logreopen" ]; then
  touch $logreopen
fi

${BINPATH}/bake -m spire.tasks spire.schema.deploy schema=platoon \
  config=${SVCPATH}/platoon/platoonapi.yaml

# improvement 6496 need to stop before running
if [[ -e ${VARPATH}/platoon.pid ]]; then
  /bin/bash -c '/bin/kill $(<${VARPATH}/platoon.pid)'
fi
sleep 2
${BINPATH}/bake -m spire.tasks spire.daemon config=${SVCPATH}/platoon/platoon.yaml
ln -sf ${SVCPATH}/platoon/platoonapi.yaml ${CONFPATH}/uwsgi/platoonapi.yaml
