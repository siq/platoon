#!/bin/sh
grep -q platoon /etc/group
if [ $? -ne 0 ]; then
  groupadd -g 1117 platoon
fi

grep -q platoon /etc/passwd
if [ $? -ne 0 ]; then
  useradd -u 1117 -g 1117 -M -N -s /bin/false platoon
fi
