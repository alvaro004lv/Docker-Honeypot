#!/bin/bash

service apache2 start

rsyslogd &

/usr/sbin/sshd -D &

sleep 2

python3 /usr/local/bin/scripts/monitor_ssh.py