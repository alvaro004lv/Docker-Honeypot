#!/bin/bash
set -e

#ssh
mkdir -p /var/log/ssh
touch /var/log/ssh/sshd.log
chmod 600 /var/log/ssh/sshd.log

/usr/sbin/sshd -D -e > /var/log/ssh/sshd.log 2>&1 &


#Samba
touch /var/log/samba/log.gateway
mkdir -p /srv/public
chmod 777 /srv/public
chown nobody:nogroup /srv/public

/usr/sbin/smbd -F --no-process-group &

# Iniciar monitorización
python3 -u /opt/monitor/monitor_gateway.py &

# Mantener el contenedor vivo
tail -f /dev/null
