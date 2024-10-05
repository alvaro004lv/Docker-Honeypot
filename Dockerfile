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

RUN python3 -m venv /opt/venv

RUN /opt/venv/bin/pip install requests

EXPOSE 22 80

COPY monitor_ssh.py /usr/local/bin/monitor_ssh.py

COPY index.html /var/www/html
COPY style.css /var/www/html

CMD ["sh", "-c", "service apache2 start && rsyslogd && /usr/sbin/sshd -D && /opt/venv/bin/python /usr/local/bin/monitor_ssh.py"]
