#!/bin/sh
logreopen=${VARPATH}/platoonapi.logreopen
if [ ! -e "$logreopen" ]; then
  touch $logreopen
fi

${BINPATH}/bake -m spire.tasks spire.schema.deploy schema=platoon \
  config=${SVCPATH}/platoon/platoon.yaml

# improvement 6496 need to stop before running
${SVCPATH}/platoon/platoon-ctl stop
sleep 2
${SVCPATH}/platoon/platoon-ctl start
ln -sf ${SVCPATH}/platoon/platoonapi.yaml ${CONFPATH}/uwsgi/platoonapi.yaml
