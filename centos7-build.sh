#!/bin/bash
interpolate() {
  perl -p -e 's/\$\{([^}]+)\}/defined $ENV{$1} ? $ENV{$1} : $&/eg; s/\$\{([^}]+)\}//eg' $1 > $2
}

python setup.py install --no-compile --record=/dev/null --prefix=${BUILDPATH}/usr --install-lib=${BUILDPATH}/usr/lib/python2.7/site-packages --install-scripts=${BUILDPATH}${BINPATH}
interpolate svc/platoon.yaml platoon.yaml.install
install -D -m 0644 platoon.yaml.install $BUILDPATH$SVCPATH/platoon/platoon.yaml

interpolate svc/platoon.monit platoon.monit.install
install -D -m 0644 platoon.monit.install $BUILDPATH$SVCPATH/platoon/platoon.monit

interpolate svc/platoon-ctl.sh platoon-ctl.sh.install
install -D -m 0755 platoon-ctl.sh.install $BUILDPATH$SVCPATH/platoon/platoon-ctl

interpolate svc/platoonapi.yaml platoonapi.yaml.install
install -D -m 0644 platoonapi.yaml.install $BUILDPATH$SVCPATH/platoon/platoonapi.yaml

interpolate svc/logrotate-platoonapi.conf logrotate-platoonapi.conf.install
install -D -m 0644 logrotate-platoonapi.conf.install $BUILDPATH/etc/logrotate.d/siq-platoonapi

interpolate svc/logrotate-platoon.conf logrotate-platoon.conf.install
install -D -m 0644 logrotate-platoon.conf.install $BUILDPATH/etc/logrotate.d/siq-platoon
