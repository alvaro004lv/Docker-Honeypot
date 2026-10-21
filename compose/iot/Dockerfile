FROM node:18-slim

WORKDIR /app

# Instalar herramientas necesarias: netcat, find, python3 y pip
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      netcat-traditional findutils python3 python3-pip && \
    npm install -g npm && \
    npm install express body-parser && \
    pip3 install --no-cache-dir requests --break-system-packages && \
    rm -rf /var/lib/apt/lists/*

# Copiar la aplicación y el script de monitorización
COPY app.js . 
COPY public ./public
COPY monitor_iot.py . 
COPY entrypoint.sh .

# Log de accesos a /set, escrito por app.js (como www-data) y leído por
# monitor_iot.py (como root) para detectar intentos de RCE en tiempo real
RUN mkdir -p /var/log/iot && \
    touch /var/log/iot/access.log && \
    chown -R www-data:www-data /var/log/iot

# Bit SUID en find para la PoC de escalada de privilegios
RUN chmod u+s /usr/bin/find && \
    chmod +x /app/entrypoint.sh && \
    chown -R www-data:www-data /app

# El contenedor arranca como root para que monitor_iot.py pueda leer /proc/<pid>/fd.
# entrypoint.sh rebaja Node a www-data mediante su.

EXPOSE 5000

# Lanzar el entrypoint: monitor en root segundo plano + node como www-data en primer plano
ENTRYPOINT ["/app/entrypoint.sh"]