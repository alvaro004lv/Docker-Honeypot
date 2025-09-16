FROM ubuntu:22.04

# Instalar SSH y Samba
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openssh-server sudo samba supervisor && \
    rm -rf /var/lib/apt/lists/*

# Crear directorios necesarios
RUN mkdir -p /var/run/sshd /var/log/supervisor /srv/public

# Crear usuarios
RUN useradd -m -s /bin/bash gateway && \
    echo 'gateway:honeypot123' | chpasswd && \
    useradd -m -s /bin/bash ituser && \
    echo 'ituser:honeypot123' | chpasswd

# Crear el archivo "pista" para el atacante
RUN echo '#!/bin/bash\nssh -p 2223 -L 8081:glpi-web:80 -L 8082:iot-vuln:5000 ituser@localhost\n# pass:honeypot123' \
    > /srv/public/tunnel.sh && chmod +x /srv/public/tunnel.sh

# Copiar configuración de Samba y supervisord
COPY smb.conf /etc/samba/smb.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Exponer puertos SSH y SMB
EXPOSE 22 445

# Lanzar supervisord (gestiona smbd + sshd)
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
