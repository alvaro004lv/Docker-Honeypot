#!/bin/bash

apt install -y python3-requests

service apache2 start

rsyslogd

/usr/sbin/sshd -D &

python3 /usr/local/bin/monitor_ssh.py
