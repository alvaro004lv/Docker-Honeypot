FROM ubuntu:latest

RUN apt-get update && apt-get install -y openssh-server rsyslog python3 python3-venv apache2 && \
    mkdir /var/run/sshd

RUN apt-get -y install python3-pip

RUN useradd -m loki && \
    echo 'loki:password123' | chpasswd

RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config && \
    echo 'AllowUsers loki' >> /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

RUN ssh-keygen -A 

RUN echo "local6.* /var/log/auth.log" >> /etc/rsyslog.conf

EXPOSE 22 80

COPY scripts /usr/local/bin/scripts

RUN chmod +x /usr/local/bin/scripts/start.sh

COPY web /var/www/html

CMD ["/usr/local/bin/scripts/start.sh"]