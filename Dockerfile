FROM ubuntu:latest

RUN apt-get update && apt-get install -y openssh-server rsyslog python3 python3-venv && \
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

EXPOSE 22

COPY monitor_ssh.py /usr/local/bin/monitor_ssh.py

CMD ["sh", "-c", "rsyslogd && /usr/sbin/sshd -D & /opt/venv/bin/python /usr/local/bin/monitor_ssh.py"]