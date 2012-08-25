#!/bin/sh
touch ${VARPATH}/platoonapi.logreopen
${BINPATH}/bake -m spire.tasks spire.schema.deploy schema=platoon \
  config=${SVCPATH}/platoon/platoon.yaml
${BINPATH}/invoke-monit start platoon
ln -sf ${SVCPATH}/platoon/platoonapi.yaml ${CONFPATH}/uwsgi/platoonapi.yaml
