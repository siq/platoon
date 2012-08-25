#!/bin/bash
interpolate() {
  perl -p -e 's/\$\{([^}]+)\}/defined $ENV{$1} ? $ENV{$1} : $&/eg; s/\$\{([^}]+)\}//eg' $1 > $2
}

$(find -L $BUILDPATH -type f -executable -name python) setup.py install

interpolate svc/platoon.yaml platoon.yaml.install
install -D -m 0644 platoon.yaml.install $BUILDPATH$SVCPATH/platoon/platoon.yaml

interpolate svc/platoon.monit platoon.monit.install
install -D -m 0644 platoon.monit.install $BUILDPATH$SVCPATH/platoon/platoon.monit

interpolate svc/platoonapi.yaml platoonapi.yaml.install
install -D -m 0644 platoonapi.yaml.install $BUILDPATH$SVCPATH/platoon/platoonapi.yaml

interpolate svc/logrotate-platoonapi.conf logrotate-platoonapi.conf.install
install -D -m 0644 logrotate-platoonapi.conf.install $BUILDPATH/etc/logrotate.d/siq-platoonapi
