#!/usr/bin/env python3
# monitor_iot.py - Detecta reverse shells activas y escaladas de privilegio via /usr/bin/find
# Dependencias: requests
# Debe ejecutarse como root para poder leer /proc/*/fd/*

import os
import re
import json
import time
import pwd
import socket
import struct
import requests
from threading import Thread

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['TELEGRAM_CHAT_ID']

CHECK_INTERVAL = 1.5
CONN_DEDUPE_TTL = 300
ESCALATION_DEDUPE_TTL = 300

ACCESS_LOG = '/var/log/iot/access.log'

# Patrones típicos de inyección de comandos en el body de POST /set
INJECTION_PATTERNS = re.compile(
    r"(;|\||&&|\$\(|`|nc\s|netcat|/dev/tcp/|bash\s+-i|sh\s+-i|wget\s|curl\s|"
    r"rm\s+-rf|chmod\s|python[23]?\s|perl\s|>\s*/tmp|cat\s+/etc)",
    re.IGNORECASE,
)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    try:
        r = requests.post(url, data=data, timeout=8)
        r.raise_for_status()
    except Exception as e:
        print("Error enviando Telegram:", e)

def hex_ip_to_str(hexip):
    hexip = hexip.strip()
    try:
        if len(hexip) == 8:
            val = int(hexip, 16)
            ip_packed = struct.pack("<I", val)
            return socket.inet_ntoa(ip_packed)
        elif len(hexip) == 32:
            raw = bytes.fromhex(hexip)
            try:
                return socket.inet_ntop(socket.AF_INET6, raw)
            except Exception:
                return hexip
        else:
            return hexip
    except Exception:
        return hexip

def parse_proc_net(path):
    """
    Lee /proc/net/tcp o /proc/net/tcp6.
    Devuelve un diccionario inode -> (ip_local, puerto_local, ip_remota, puerto_remoto, estado)
    """
    out = {}
    try:
        with open(path, 'r') as f:
            next(f)
            for line in f:
                cols = line.split()
                if len(cols) < 10:
                    continue
                local, rem, state, inode = cols[1], cols[2], cols[3], cols[9]
                try:
                    lip_h, lport_h = local.split(':')
                    rip_h, rport_h = rem.split(':')
                except ValueError:
                    continue
                lip = hex_ip_to_str(lip_h)
                rip = hex_ip_to_str(rip_h)
                try:
                    lport = int(lport_h, 16)
                    rport = int(rport_h, 16)
                except Exception:
                    lport = 0; rport = 0
                out[inode] = (lip, lport, rip, rport, state)
    except FileNotFoundError:
        pass
    except Exception as e:
        print("Error parseando", path, e)
    return out

def build_socket_table():
    """Combina tcp y tcp6 en un único diccionario inode -> tupla(...)"""
    t = {}
    for p in ("/proc/net/tcp", "/proc/net/tcp6"):
        t.update(parse_proc_net(p))
    return t

def readlink_safe(path):
    try:
        return os.readlink(path)
    except Exception:
        return ""

def find_pid_by_inode(inode):
    """Localiza el PID cuyo /proc/<pid>/fd/* enlaza con socket:[inode]"""
    for pid in os.listdir("/proc"):
        if not pid.isdigit(): continue
        fd_dir = f"/proc/{pid}/fd"
        try:
            for fd in os.listdir(fd_dir):
                link = readlink_safe(os.path.join(fd_dir, fd))
                if link == f"socket:[{inode}]":
                    return int(pid)
        except Exception:
            continue
    return None

def uid_of_pid(pid):
    try:
        with open(f"/proc/{pid}/status") as f:
            for ln in f:
                if ln.startswith("Uid:"):
                    parts = ln.split()
                    # parts[1] uid real, parts[2] uid efectivo
                    return int(parts[2])
    except Exception:
        pass
    return None

def cmdline_of_pid(pid):
    try:
        with open(f"/proc/{pid}/cmdline", 'rb') as f:
            data = f.read().replace(b'\x00', b' ')
            return data.decode(errors='ignore').strip()
    except Exception:
        return ""

def parent_pid(pid):
    try:
        with open(f"/proc/{pid}/status") as f:
            for ln in f:
                if ln.startswith("PPid:"):
                    return int(ln.split()[1])
    except Exception:
        pass
    return None

def ancestor_cmdlines(pid, depth=8):
    res = []
    cur = pid
    for _ in range(depth):
        p = parent_pid(cur)
        if not p or p == 0:
            break
        res.append((p, cmdline_of_pid(p)))
        cur = p
    return res

SHELL_PATTERNS = ["nc ", "netcat", "-e /bin/sh", "-e/bin/sh", "/dev/tcp/", "bash -i", "sh -i", "-c nc ", "-c netcat"]


def matches_shell_pattern(cl):
    return any(p in cl for p in SHELL_PATTERNS)


# Detección basada en sockets ESTABLISHED y procesos sospechosos
def detect_reverse_shells_by_process(seen_conns, www_uid):
    """
    Recorre todos los procesos de www-data con un socket TCP en estado
    ESTABLISHED y comprueba si el propio proceso, o alguno de sus ancestros,
    coincide con un patrón típico de reverse shell (nc, netcat, -e /bin/sh,
    /dev/tcp/, bash -i, sh -i).

    OJO: con "nc ... -e /bin/sh", netcat hace fork+exec — el proceso que
    termina sosteniendo el socket (el /bin/sh final, con el socket duplicado
    en sus fds 0/1/2) tiene un cmdline que es solo "sh", SIN "nc" en ningún
    sitio; el "nc" solo aparece en el cmdline del proceso PADRE. Si solo se
    mira el cmdline del propio proceso (como hacía la versión anterior), la
    reverse shell nunca se detecta. Por eso aquí se recorre también la
    cadena de ancestros, igual que ya hace detect_find_escalation().
    """
    results = []
    sock_table = build_socket_table()
    # recorrer todos los procesos activos
    for entry in os.listdir("/proc"):
        if not entry.isdigit(): continue
        pid = int(entry)
        cl = cmdline_of_pid(pid).lower()
        if not cl:
            continue
        # Verificar que el proceso pertenece a www-data
        uid = uid_of_pid(pid)
        if uid != www_uid:
            continue

        # Sospechoso si el propio proceso o algún ancestro coincide con un
        # patrón de reverse shell
        ancestors = ancestor_cmdlines(pid, depth=6)
        suspicious = matches_shell_pattern(cl) or any(
            matches_shell_pattern(acmd.lower()) for (_apid, acmd) in ancestors
        )
        if not suspicious:
            continue

        # Inspeccionar los descriptores de fichero del proceso
        fd_dir = f"/proc/{pid}/fd"
        try:
            for fd in os.listdir(fd_dir):
                link = readlink_safe(os.path.join(fd_dir, fd))
                if link.startswith("socket:[") and link.endswith("]"):
                    inode = link[len("socket:["):-1]
                    entry = sock_table.get(inode)
                    if not entry:
                        continue
                    lip, lport, rip, rport, state = entry
                    if state == "01":  # conexión ESTABLISHED
                        key = f"{pid}:{inode}:{rip}:{rport}"
                        if key not in seen_conns:
                            seen_conns[key] = time.time()
                            results.append((pid, cl, lip, lport, rip, rport, inode))
        except Exception:
            continue
    # Limpiar entradas expiradas de la caché de deduplicación
    now = time.time()
    for k, t in list(seen_conns.items()):
        if now - t > CONN_DEDUPE_TTL:
            del seen_conns[k]
    return results

def detect_find_escalation(seen_escalations):
    res = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit(): continue
        pid = int(entry)
        cmd = cmdline_of_pid(pid)
        if not cmd: continue
        basename = os.path.basename(cmd.split()[0]) if cmd else ""
        # solo shells
        if basename not in ("sh", "bash", "/bin/sh", "/bin/bash"):
            continue
        euid = uid_of_pid(pid)
        if euid != 0:
            continue
        ancestors = ancestor_cmdlines(pid, depth=6)
        found_find = any("/usr/bin/find" in (acmd.lower()) for (_apid, acmd) in ancestors)
        if found_find:
            if pid not in seen_escalations or time.time() - seen_escalations[pid] > ESCALATION_DEDUPE_TTL:
                seen_escalations[pid] = time.time()
                res.append((pid, cmd, ancestors))
    # Limpiar entradas antiguas del histórico
    now = time.time()
    for k, t in list(seen_escalations.items()):
        if now - t > ESCALATION_DEDUPE_TTL:
            del seen_escalations[k]
    return res

def tail_file(path, retries=30, delay=2):
    for _ in range(retries):
        try:
            f = open(path, 'r')
            f.seek(0, 2)
            return f
        except FileNotFoundError:
            time.sleep(delay)
    raise RuntimeError(f"Log {path} not available")


def is_plain_number(value):
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def monitor_set_endpoint():
    """
    Analiza cada POST /set registrado por app.js. El endpoint pasa 'value'
    directamente a child_process.exec() sin sanitizar: cualquier valor que no
    sea un número simple es, por definición, un intento de inyección de
    comandos / RCE, se establezca o no una shell después.
    """
    try:
        f = tail_file(ACCESS_LOG)
    except RuntimeError as e:
        print(e)
        return

    while True:
        line = f.readline()
        if not line:
            time.sleep(0.5)
            continue
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        value = str(entry.get('value', ''))
        ip = entry.get('ip', '?')

        if not is_plain_number(value):
            tag = "🎯 Posible inyección de comandos" if INJECTION_PATTERNS.search(value) \
                else "⚠️ Valor no numérico"
            msg = (f"{tag} en POST /set del IoT (RCE endpoint)\n"
                   f"  Origen: {ip}\n"
                   f"  Payload: {value[:300]}")
            print(msg)
            send_telegram_message(msg)


def main_loop():
    try:
        www_uid = pwd.getpwnam("www-data").pw_uid
    except KeyError:
        print("Usuario www-data no existe. Abortando.")
        return

    seen_conns = {}
    seen_escalations = {}

    print("Monitor IoT iniciado. Ejecutar como root para detectar sockets. Interval:", CHECK_INTERVAL)
    while True:
        try:
            # Reverse shells basadas en procesos + sockets ESTABLISHED
            conns = detect_reverse_shells_by_process(seen_conns, www_uid)
            for pid, cl, lip, lport, rip, rport, inode in conns:
                msg = (f"🔔 Reverse shell ESTABLECIDA detectada (www-data): PID={pid}\n"
                       f"cmdline='{cl}'\nlocal={lip}:{lport} remote={rip}:{rport} inode={inode}")
                print(msg)
                send_telegram_message(msg)
        except Exception as e:
            print("Error monitorizando reverse shell:", e)

        try:
            escs = detect_find_escalation(seen_escalations)
            for pid, cmd, ancestors in escs:
                anc_str = " -> ".join(f"{apid}:{acmd}" for (apid, acmd) in ancestors)
                msg = (f"🔺 Escalada a root detectada: PID={pid}, cmdline='{cmd}'\nAncestros: {anc_str}")
                print(msg)
                send_telegram_message(msg)
        except Exception as e:
            print("Error monitorizando find:", e)

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    Thread(target=monitor_set_endpoint, daemon=True).start()
    main_loop()
