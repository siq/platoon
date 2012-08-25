#!/bin/sh
logreopen=${VARPATH}/platoonapi.logreopen
if [[ ! -e "$logreopen" ]]; then
  touch $logreopen
fi

${BINPATH}/bake -m spire.tasks spire.schema.deploy schema=platoon \
  config=${SVCPATH}/platoon/platoon.yaml

${BINPATH}/invoke-monit start platoon
ln -sf ${SVCPATH}/platoon/platoonapi.yaml ${CONFPATH}/uwsgi/platoonapi.yaml
