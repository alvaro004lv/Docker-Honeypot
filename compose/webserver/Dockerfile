FROM php:7.3-apache

# Instalar extensiones necesarias para GLPI y Python
RUN apt-get update && apt-get install -y \
    libpng-dev \
    libjpeg-dev \
    libfreetype6-dev \
    libonig-dev \
    libzip-dev \
    zip \
    unzip \
    python3 \
    python3-pip \
    && docker-php-ext-configure gd \
        --with-freetype-dir=/usr/include/ \
        --with-jpeg-dir=/usr/include/ \
    && docker-php-ext-install gd mysqli pdo pdo_mysql zip \
    && pip3 install --no-cache-dir requests pymysql \
    && rm -rf /var/lib/apt/lists/*

# Habilitar módulos de Apache
RUN a2enmod rewrite && a2enmod status

# La imagen base trae AllowOverride None por defecto, así que los .htaccess
# del proyecto no se aplican nunca. Sin esto Apache sirve el .php subido como
# texto plano en vez de ejecutarlo, y la webshell no funciona.
RUN { \
        echo '<Directory /var/www/html>'; \
        echo '    Options Indexes FollowSymLinks'; \
        echo '    AllowOverride All'; \
        echo '    Require all granted'; \
        echo '</Directory>'; \
    } > /etc/apache2/conf-available/allow-override.conf && \
    a2enconf allow-override

# access.log/error.log vienen enlazados a /dev/stdout y /dev/stderr, y esos
# streams no se pueden hacer seek. monitor_webserver.py necesita seek(0,2)
# para tailear el log, así que los cambiamos por ficheros normales.
RUN mkdir -p /var/log/apache2 && \
    rm -f /var/log/apache2/access.log /var/log/apache2/error.log && \
    touch /var/log/apache2/access.log /var/log/apache2/error.log && \
    chmod 644 /var/log/apache2/access.log /var/log/apache2/error.log

# Copiar GLPI al contenedor
COPY glpi /var/www/html

# Copiar el script de monitorización y el entrypoint
COPY monitor_webserver.py /app/monitor_webserver.py
COPY entrypoint.sh /app/entrypoint.sh

# Permisos para el usuario www-data
RUN chown -R www-data:www-data /var/www/html \
    && chmod +x /app/monitor_webserver.py /app/entrypoint.sh

# Directorio de trabajo para scripts
WORKDIR /app

# El entrypoint instala el esquema de GLPI (si hace falta) antes de arrancar
# Apache y el monitor: sin esto la base de datos queda vacía y GLPI nunca
# sale del asistente de instalación.
CMD ["/app/entrypoint.sh"]


# Copiar configuración personalizada de Apache
#COPY apache2.conf /etc/apache2/apache2.conf
#COPY 000-default.conf /etc/apache2/sites-available/000-default.conf

# Crear carpeta /files y permitir acceso web
#RUN mkdir -p /var/www/html/files && \
    #chmod -R 777 /var/www/html/files && \
    #chown -R www-data:www-data /var/www/html/files

# Desactivar protección por .htaccess en /files
#RUN echo '' > /var/www/html/files/.htaccess
