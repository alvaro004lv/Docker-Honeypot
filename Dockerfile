# Utilizar Ubuntu como base
FROM ubuntu:latest

# Instalar OpenSSH Server y rsyslog
RUN apt-get update && apt-get install -y openssh-server rsyslog python3 && \
    mkdir /var/run/sshd

# Crear un nuevo usuario 'loki' y establecer una contraseña débil
RUN useradd -m loki && \
    echo 'loki:password123' | chpasswd

# Permitir inicio de sesión del usuario 'loki' y habilitar acceso por contraseña
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config && \
    echo 'AllowUsers loki' >> /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Generar claves de host para SSH
RUN ssh-keygen -A 

# Configurar rsyslog para registrar logs de SSH
RUN echo "local6.* /var/log/auth.log" >> /etc/rsyslog.conf

# Exponer el puerto 22 para SSH
EXPOSE 22

# Copiar el script de monitoreo al contenedor
COPY monitor_ssh.py /usr/local/bin/monitor_ssh.py

# Comando para iniciar rsyslog en primer plano y el servidor SSH
CMD ["sh", "-c", "rsyslogd && /usr/sbin/sshd -D"]
# & python3 /usr/local/bin/monitor_ssh.py