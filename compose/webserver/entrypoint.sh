#!/bin/sh
# No pongo "set -e" porque aquí hay pasos que fallan a propósito (DB que
# todavía no responde, tabla que aún no existe) y con errexit el script
# se corta de golpe sin avisar.

# Esperar a que MySQL acepte conexiones antes de instalar GLPI.
# OJO: "php -r" siempre sale con 0 aunque mysqli lance un Warning de
# conexión, así que hay que mirar $m->connect_error a mano.
echo "Esperando a MySQL (db:3306)..."
for i in $(seq 1 60); do
    php -r "
        \$m = @new mysqli('db', 'glpi', 'glpi', 'glpi');
        exit(\$m->connect_error ? 1 : 0);
    " 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "MySQL listo."
        break
    fi
    sleep 2
done

# Instalar el esquema de GLPI si todavía no existe. Es idempotente: si ya
# está instalado, db:install falla con "already installed" y no pasa nada.
# Sin esto la base de datos se queda vacía y GLPI se queda en el asistente
# de instalación inicial.
php -r "
    \$m = @new mysqli('db', 'glpi', 'glpi', 'glpi');
    if (\$m->connect_error) { exit(1); }
    \$r = @\$m->query('SELECT 1 FROM glpi_configs LIMIT 1');
    exit(\$r ? 0 : 1);
" 2>/dev/null
already_installed=$?

if [ "$already_installed" != "0" ]; then
    echo "Instalando esquema de GLPI..."
    # Tiene que correr como www-data. Si corre como root, los ficheros de
    # caché que genera (files/_cache/cache_trans/*.dat) quedan con dueño
    # root y Apache luego no puede leerlos: la página se corta a medias
    # sin dar ningún error.
    su -s /bin/sh www-data -c "
        php /var/www/html/bin/console db:install \
            --db-host=db --db-name=glpi --db-user=glpi --db-password=glpi \
            --no-interaction --force
    "
    echo "db:install terminado (exit=$?)."
else
    echo "GLPI ya está instalado, se omite db:install."
fi

# Por si algún fichero se quedó con otro dueño, se arregla antes de arrancar Apache.
chown -R www-data:www-data /var/www/html/files /var/www/html/config 2>/dev/null

python3 -u /app/monitor_webserver.py &
exec apache2-foreground
