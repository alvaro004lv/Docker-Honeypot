#!/bin/sh
# entrypoint.sh
# monitor_iot.py runs as root (needs /proc/<pid>/fd access for reverse-shell detection)
# node/app.js drops to www-data via su

python3 -u /app/monitor_iot.py &

# Drop Node to www-data while keeping the monitor above as root
exec su -s /bin/sh www-data -c "exec node /app/app.js"
