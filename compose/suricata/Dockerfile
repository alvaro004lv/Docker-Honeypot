FROM python:3.12-slim

# Instalar Suricata y sus dependencias
RUN apt-get update && \
    apt-get install -y suricata iproute2 && \
    pip install requests --break-system-packages && \
    mkdir -p /etc/suricata/rules /var/log/suricata /var/run/suricata && \
    rm -rf /var/lib/apt/lists/*

# Copiar configuración, reglas y script de alertas
COPY suricata.yaml /etc/suricata/suricata.yaml
COPY rules/ /var/lib/suricata/rules/
COPY telegram_alerts.py /telegram_alerts.py

# Suricata requiere NET_ADMIN y NET_RAW para captura AF_PACKET; el proceso corre como root
CMD ["sh", "-c", "suricata -c /etc/suricata/suricata.yaml -i eth0 -l /var/log/suricata --runmode=autofp & python -u /telegram_alerts.py"]
