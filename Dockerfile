FROM ubuntu:latest

RUN apt-get update && apt-get install -y openssh-server rsyslog python3 python3-pip apache2 libapache2-mod-wsgi-py3 && \
    mkdir /var/run/sshd

RUN useradd -m loki && \
    echo 'loki:password123' | chpasswd

RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config && \
    echo 'AllowUsers loki' >> /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

RUN ssh-keygen -A 

RUN echo "local6.* /var/log/auth.log" >> /etc/rsyslog.conf

EXPOSE 22 80

COPY scripts /usr/local/bin/scripts
RUN pip3 install -r /usr/local/bin/scripts/requirements.txt --break-system-packages

RUN chmod +x /usr/local/bin/scripts/start.sh

COPY apache /etc/apache2/sites-available/
COPY web /var/www/html

RUN a2ensite flaskapp && a2enmod wsgi

RUN chown -R www-data:www-data /var/www/html && \
    chmod -R 755 /var/www/html
RUN mkdir /var/www/html/instance && \
    chown www-data:www-data /var/www/html/instance

CMD ["/usr/local/bin/scripts/start.sh"]
