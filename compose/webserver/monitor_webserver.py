import os
import re
import time
import pymysql
import requests
from threading import Thread

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['TELEGRAM_CHAT_ID']

# Log de acceso de Apache (generado por apache2-foreground)
APACHE_LOG = '/var/log/apache2/access.log'

# Patrones de inyección SQL a buscar en las URIs del log
SQLI_PATTERNS = re.compile(
    r"(union\s+select|or\s+1=1|'\s*--|\bselect\b.*\bfrom\b|"
    r"drop\s+table|insert\s+into|exec\s*\(|xp_cmdshell|information_schema|"
    r"load_file\s*\(|sleep\s*\(|benchmark\s*\(|@@datadir|@@version)",
    re.IGNORECASE,
)

# Patrones de XSS a buscar en URIs y en el contenido de tickets
XSS_PATTERNS = re.compile(
    r"(<script|onerror\s*=|onload\s*=|javascript:|<img[^>]+onerror|<svg[^>]+onload)",
    re.IGNORECASE,
)

# Rutas que indican actividad relevante del atacante
INTERESTING_PATHS = [
    '/front/user_search.php',
    '/front/upload_attachment.php',
    '/files/uploads/',
    '/front/login.php',
    '/front/document.form.php',
]

# Rutas de reconocimiento / exposición de información sensible
RECON_PATHS = [
    '/info.php',
    '/files/PHP/',
    '/status.php',
]


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error enviando mensaje a Telegram: {e}")


def tail_file(path, retries=30, delay=2):
    for _ in range(retries):
        try:
            f = open(path, 'r')
            f.seek(0, 2)
            return f
        except FileNotFoundError:
            time.sleep(delay)
    raise RuntimeError(f"Log {path} not available")


def monitor_apache_log():
    """Analiza el access.log de Apache en busca de indicadores de ataque y eventos de login."""
    try:
        f = tail_file(APACHE_LOG)
    except RuntimeError as e:
        print(e)
        return

    while True:
        line = f.readline()
        if not line:
            time.sleep(0.5)
            continue

        line_stripped = line.strip()

        # Extraer método y ruta del Combined Log Format:
        #   127.0.0.1 - - [01/Jan/2024:00:00:00 +0000] "GET /path HTTP/1.1" 200 1234
        m = re.search(r'"(\w+)\s+([^\s"]+)\s+HTTP', line_stripped)
        if not m:
            continue

        method = m.group(1)
        path   = m.group(2)

        # Inyección SQL en la URI
        if SQLI_PATTERNS.search(path):
            send_telegram_message(
                f"💉 Posible SQL Injection detectada en GLPI\n"
                f"  Método: {method}\n"
                f"  URI: {path[:300]}\n"
                f"  Log: {line_stripped[:400]}"
            )

        # Intento de login
        elif '/front/login.php' in path and method == 'POST':
            send_telegram_message(
                f"🔑 Intento de login en GLPI\n"
                f"  Log: {line_stripped[:300]}"
            )

        # Subida de fichero
        elif '/front/upload_attachment.php' in path and method == 'POST':
            send_telegram_message(
                f"📤 Subida de fichero vía página de adjuntos de GLPI\n"
                f"  Log: {line_stripped[:300]}"
            )

        # Webshell / PHP subido ejecutado
        elif '/files/uploads/' in path and path.lower().endswith(
            ('.php', '.phtml', '.php5', '.phar')
        ):
            send_telegram_message(
                f"🚨 Posible webshell ejecutada en GLPI!\n"
                f"  URI: {path}\n"
                f"  Log: {line_stripped[:300]}"
            )

        # Búsqueda de usuarios (vector SQLi)
        elif '/front/user_search.php' in path:
            send_telegram_message(
                f"🔍 Acceso a búsqueda de usuarios (SQLi vector)\n"
                f"  URI: {path[:300]}\n"
                f"  Log: {line_stripped[:300]}"
            )

        # XSS reflejado en la URI (por ejemplo probado directamente por curl/sqlmap/etc.)
        if XSS_PATTERNS.search(path):
            send_telegram_message(
                f"🕸️ Posible XSS detectado en GLPI\n"
                f"  Método: {method}\n"
                f"  URI: {path[:300]}\n"
                f"  Log: {line_stripped[:400]}"
            )

        # Reconocimiento / exposición de información (phpinfo, status.php...)
        for recon in RECON_PATHS:
            if recon in path:
                send_telegram_message(
                    f"🕵️ Acceso a endpoint de reconocimiento/información sensible\n"
                    f"  URI: {path[:300]}\n"
                    f"  Log: {line_stripped[:300]}"
                )
                break


def monitor_sessions(session_dir="/var/www/html/files/_sessions"):
    seen_sessions = set()
    while True:
        try:
            current_sessions = set(os.listdir(session_dir))
            new_sessions = current_sessions - seen_sessions
            for session_file in new_sessions:
                send_telegram_message(f"🟢 Nuevo login en GLPI: sesión {session_file}")
            seen_sessions = current_sessions
        except FileNotFoundError:
            pass
        time.sleep(2)


def monitor_tickets(db_host="db", db_user="glpi", db_password="glpi", db_name="glpi"):
    last_ticket_id = 0
    while True:
        try:
            conn = pymysql.connect(
                host=db_host, user=db_user, password=db_password,
                database=db_name, connect_timeout=5,
            )
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, content FROM glpi_tickets "
                "WHERE id > %s ORDER BY id ASC LIMIT 20",
                (last_ticket_id,),
            )
            rows = cursor.fetchall()
            for row in rows:
                ticket_id, name, content = row
                send_telegram_message(
                    f"🎫 Nuevo ticket en GLPI:\n"
                    f"  ID={ticket_id}\n"
                    f"  Título={name}\n"
                    f"  Contenido={str(content)[:300]}"
                )
                if XSS_PATTERNS.search(str(name) or '') or XSS_PATTERNS.search(str(content) or ''):
                    send_telegram_message(
                        f"🕸️ Stored XSS detectado en ticket GLPI (ID={ticket_id})\n"
                        f"  Payload en título: {str(name)[:200]}\n"
                        f"  Payload en contenido: {str(content)[:200]}"
                    )
                last_ticket_id = max(last_ticket_id, ticket_id)
            conn.close()
        except Exception as e:
            print(f"Error monitorizando tickets: {e}")
        time.sleep(3)


if __name__ == "__main__":
    threads = [
        Thread(target=monitor_sessions,  daemon=True),
        Thread(target=monitor_tickets,   daemon=True),
        Thread(target=monitor_apache_log, daemon=True),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
