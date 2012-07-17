#!/bin/bash
$(find -L $BUILDPATH -type f -executable -name python) setup.py install

perl -p -e 's/\$\{([^}]+)\}/defined $ENV{$1} ? $ENV{$1} : $&/eg; s/\$\{([^}]+)\}//eg' svc/platoon.yaml > platoon.yaml.install
install -D -m 0644 platoon.yaml.install $BUILDPATH$SVCPATH/platoon/platoon.yaml

perl -p -e 's/\$\{([^}]+)\}/defined $ENV{$1} ? $ENV{$1} : $&/eg; s/\$\{([^}]+)\}//eg' svc/platoon.monit > platoon.monit.install
install -D -m 0644 platoon.monit.install $BUILDPATH$SVCPATH/platoon/platoon.monit

perl -p -e 's/\$\{([^}]+)\}/defined $ENV{$1} ? $ENV{$1} : $&/eg; s/\$\{([^}]+)\}//eg' svc/platoonapi.yaml > platoonapi.yaml.install
install -D -m 0644 platoonapi.yaml.install $BUILDPATH$SVCPATH/platoon/platoonapi.yaml
