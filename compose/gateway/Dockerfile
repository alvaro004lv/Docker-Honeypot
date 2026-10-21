FROM ubuntu:22.04

# Instalar SSH, Samba, Python, pip y rsyslog
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        openssh-server sudo samba python3 python3-pip rsyslog && \
    rm -rf /var/lib/apt/lists/*

# Crear directorios necesarios
RUN mkdir -p /var/run/sshd /opt/monitor

# Crear usuarios
RUN useradd -m -s /bin/bash gateway && \
    echo 'gateway:honeypot123' | chpasswd && \
    useradd -m -s /bin/bash ituser && \
    echo 'ituser:honeypot123' | chpasswd

# Estructura del recurso SMB (carpeta compartida de IT)
RUN mkdir -p \
    /srv/public/IT_Department/Documentation \
    /srv/public/IT_Department/Infrastructure/Network \
    /srv/public/IT_Department/Infrastructure/Servers \
    /srv/public/IT_Department/Security/Policies \
    /srv/public/IT_Department/Security/Credentials \
    /srv/public/IT_Department/Projects/Onboarding \
    /srv/public/IT_Department/Software/Licenses \
    /srv/public/IT_Department/Software/Installers \
    /srv/public/IT_Department/Helpdesk/Templates \
    /srv/public/IT_Department/Scripts/Maintenance \
    /srv/public/IT_Department/Scripts/Deployment

# Top-level README
RUN printf '=== IT Department Shared Drive ===\n\nThis share is maintained by the IT team.\nFor support: helpdesk@techcorp.internal  |  ext. 2210\n\nFolders:\n  Documentation/   -- IT procedures and runbooks\n  Infrastructure/  -- Network diagrams, server inventory\n  Security/        -- Policies and access credentials\n  Projects/        -- Active IT projects\n  Software/        -- Licenses and approved installers\n  Helpdesk/        -- Ticket templates and scripts\n  Scripts/         -- Maintenance and deployment scripts\n' \
    > /srv/public/IT_Department/README.txt

# Documentation
RUN printf '# IT Onboarding Checklist\n\n1. Create AD account (tickets in GLPI)\n2. Assign laptop from asset pool\n3. VPN profile – see Documentation/VPN_Setup.md\n4. GLPI access: http://glpi-web  glpi/glpi (change on first login)\n5. Email setup: Exchange server 172.28.0.10\n6. Add to distribution list: it-team@techcorp.internal\n' \
    > /srv/public/IT_Department/Documentation/IT_Onboarding_Checklist.txt

RUN printf '# Network & Firewall Runbook v2.3\n\nContact: netops@techcorp.internal\n\n## Core Switches\n  SW-CORE-01  172.28.0.1  (Cisco Catalyst 3850)\n  SW-CORE-02  172.28.0.2  (Cisco Catalyst 3850)\n\n## Servers\n  DC-01       172.28.0.5   Windows Server 2019 AD/DNS\n  GLPI-WEB    172.28.0.20  GLPI IT Management (port 80)\n  IOT-GW      172.28.0.30  IoT Gateway / BMS (port 5000)\n  BACKUP-01   172.28.0.50  Veeam Backup\n\n## Firewall\n  FW-01  172.28.0.254  FortiGate 100F\n  Admin: https://172.28.0.254  admin / see Security/Credentials/\n' \
    > /srv/public/IT_Department/Documentation/Network_Runbook.txt

RUN printf '# Password Reset Procedure\n\n1. User submits ticket in GLPI with manager approval.\n2. Helpdesk verifies identity via employee ID.\n3. Reset in AD with temp password: TechCorp@<EmployeeID>\n4. User must change on next login.\n\nEscalation: sysadmin@techcorp.internal\n' \
    > /srv/public/IT_Department/Documentation/Password_Reset_Procedure.txt

# Infrastructure/Network
RUN printf '# Network Inventory\n\nVLAN 10 – Management    172.28.0.0/24\nVLAN 20 – Servers       172.28.1.0/24\nVLAN 30 – Workstations  172.28.2.0/24\nVLAN 40 – IoT/BMS       172.28.3.0/24\nVLAN 99 – DMZ           10.0.99.0/24\n\nDNS: 172.28.0.5 (internal), 8.8.8.8 (external fallback)\nNTP: 172.28.0.5\nProxy: 172.28.0.15:3128\n' \
    > /srv/public/IT_Department/Infrastructure/Network/VLAN_Inventory.txt

RUN printf '# WiFi Credentials (Internal Use Only)\n\nSSID: TechCorp-Corp   Key: C0rpW1f1#2024!\nSSID: TechCorp-Guest  Key: Guest@2024\nSSID: TechCorp-IoT    Key: IoT_Net_2024!\n\nWPA2-Enterprise radius: 172.28.0.5:1812\n  service account: radius_svc  pass: R4d1us$vc!\n' \
    > /srv/public/IT_Department/Infrastructure/Network/WiFi_Credentials.txt

# Infrastructure/Servers
RUN printf '# Server Inventory Q3-2024\n\nHostname       IP            OS                    Role\n----------------------------------------------------------------------\nDC-01          172.28.0.5    Windows Server 2019   AD / DNS / DHCP\nGLPI-WEB       172.28.0.20   Debian 11             GLPI Helpdesk\nBACKUP-01      172.28.0.50   Windows Server 2022   Veeam B&R\nIOT-GW         172.28.0.30   Ubuntu 22.04          IoT/BMS Gateway\nDB-01          172.28.0.21   Debian 11             MySQL (GLPI DB)\nFILE-01        172.28.0.22   Ubuntu 22.04          Samba File Server\n' \
    > /srv/public/IT_Department/Infrastructure/Servers/Server_Inventory.txt

# Security/Policies
RUN printf '# Information Security Policy v1.4\n\nApproved by: CTO – 2024-01-15\n\n1. All passwords minimum 12 chars, rotated every 90 days.\n2. MFA required for all remote access.\n3. No local admin rights on workstations.\n4. All servers patched within 30 days of release.\n5. GLPI used for all asset and ticket management.\n6. VPN mandatory for remote work (FortiClient).\n7. USB storage prohibited without written approval.\n' \
    > /srv/public/IT_Department/Security/Policies/Information_Security_Policy.txt

# Seguridad/Credenciales: fichero cebo con la pista del túnel SSH
RUN printf '# Remote Access – IT Staff Only\n# Last updated: 2024-09-01  by: sysadmin\n\n## SSH Gateway\nHost: gateway.techcorp.internal  (external: <public-ip>:2223)\nUser: ituser\nPass: honeypot123\n\n## Internal Services (accessible via SSH tunnel after login)\nGLPI Helpdesk :  ssh -L 8081:glpi-web:80 ituser@gateway\nIoT / BMS     :  ssh -L 8082:iot-vuln:5000 ituser@gateway\n\n## Tunnel helper script\nSee: Scripts/Maintenance/tunnel.sh\n' \
    > /srv/public/IT_Department/Security/Credentials/remote_access.txt

# Scripts – el script cebo del túnel se deja aquí para que sea descubierto vía SMB
RUN printf '#!/bin/bash\n# SSH tunnel – opens GLPI (8081) and IoT dashboard (8082) locally\n# Usage: bash tunnel.sh\nssh -p 2223 \\\n  -L 8081:glpi-web:80 \\\n  -L 8082:iot-vuln:5000 \\\n  ituser@localhost\n# pass: honeypot123\n' \
    > /srv/public/IT_Department/Scripts/Maintenance/tunnel.sh && \
    chmod +x /srv/public/IT_Department/Scripts/Maintenance/tunnel.sh

# Mantener la ruta original para el monitor SMB (monitor_gateway.py vigila el acceso a tunnel.sh)
RUN ln -s /srv/public/IT_Department/Scripts/Maintenance/tunnel.sh \
         /srv/public/tunnel.sh

RUN printf '# Deployment Scripts\n\n- deploy_glpi.sh     : GLPI full install (run on DB-01 + GLPI-WEB)\n- patch_servers.sh   : Unattended apt upgrade all Linux hosts\n- backup_trigger.sh  : Manual Veeam backup trigger\n\nAll scripts require sudo. Log to /var/log/it_scripts.log\n' \
    > /srv/public/IT_Department/Scripts/Deployment/README.txt

# Software
RUN printf '# Software Licenses\n\nProduct              License Key                       Seats  Expiry\n------------------------------------------------------------------------\nWindows Server 2019  XXXXX-XXXXX-XXXXX-XXXXX-XXXXX     10     2027-01\nOffice 365 E3        (see M365 admin portal)            80     2025-06\nFortiClient VPN      FC-10-00XXX-000-00-XX              80     2025-12\nVeeam B&R v12        See IT safe (Building A, 3rd fl)    -     2026-03\n' \
    > /srv/public/IT_Department/Software/Licenses/Software_Licenses.txt

# Helpdesk templates
RUN printf 'Subject: [HELPDESK] Password Reset Request\n\nDear IT,\n\nPlease reset the password for user: _______________\nEmployee ID: _______________\nManager approval: _______________\n\nThanks,\n' \
    > /srv/public/IT_Department/Helpdesk/Templates/Password_Reset_Request.txt

# Projects
RUN printf '# New Employee Onboarding – Template\n\nEmployee: _______________\nStart date: _______________\nManager: _______________\n\nChecklist:\n[ ] AD account created\n[ ] Laptop provisioned (asset tag: ___)\n[ ] GLPI user created (profile: Self-Service)\n[ ] Email configured\n[ ] VPN token issued\n[ ] Security policy signed\n' \
    > /srv/public/IT_Department/Projects/Onboarding/New_Employee_Template.txt

# Establecer permisos en toda la carpeta compartida
RUN chmod -R 755 /srv/public && \
    chown -R nobody:nogroup /srv/public

# Configurar SSH
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config && \
    echo 'AllowUsers gateway ituser' >> /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Configurar rsyslog para auth.log
RUN echo "local6.* /var/log/auth.log" >> /etc/rsyslog.conf && \
    touch /var/log/auth.log && chmod 600 /var/log/auth.log

# Copiar configuración de Samba
COPY smb.conf /etc/samba/smb.conf

# Copiar script de monitorización y start.sh
COPY monitor_gateway.py /opt/monitor/monitor_gateway.py
COPY start.sh /opt/monitor/start.sh
RUN chmod +x /opt/monitor/monitor_gateway.py /opt/monitor/start.sh

# Instalar librería HTTP para las alertas Telegram
RUN pip3 install requests

# Exponer puertos de SSH y SMB/NetBIOS
EXPOSE 22 445

# Arrancar todos los servicios
CMD ["/opt/monitor/start.sh"]
