FROM php:7.3-apache

# Instalar extensiones necesarias para GLPI
RUN apt-get update && apt-get install -y \
    libpng-dev \
    libjpeg-dev \
    libfreetype6-dev \
    libonig-dev \
    libzip-dev \
    zip \
    unzip \
    && docker-php-ext-configure gd \
        --with-freetype-dir=/usr/include/ \
        --with-jpeg-dir=/usr/include/ \
    && docker-php-ext-install gd mysqli pdo pdo_mysql zip

# Habilitar módulo rewrite de Apache
RUN a2enmod rewrite

COPY glpi /var/www/html

RUN chown -R www-data:www-data /var/www/html

# Copiar configuración personalizada de Apache
#COPY apache2.conf /etc/apache2/apache2.conf
#COPY 000-default.conf /etc/apache2/sites-available/000-default.conf

# Crear carpeta /files y permitir acceso web
#RUN mkdir -p /var/www/html/files && \
    #chmod -R 777 /var/www/html/files && \
    #chown -R www-data:www-data /var/www/html/files

# Desactivar protección por .htaccess en /files
#RUN echo '' > /var/www/html/files/.htaccess
