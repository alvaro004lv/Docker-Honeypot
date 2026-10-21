import os
import time
import requests
import json
from collections import Counter

LOG_FILE = "/var/log/suricata/eve.json"
TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_TOKEN']
TELEGRAM_CHAT_ID = os.environ['TELEGRAM_CHAT_ID']

# Enviar alerta Telegram cuando se acumule esta cantidad de alertas en TIME_WINDOW segundos
ALERT_THRESHOLD = 5
TIME_WINDOW = 10

# Firmas de alta severidad (herramientas de ataque / fuerza bruta) que se
# notifican al instante, sin esperar a que se acumule el umbral de la ventana.
CRITICAL_KEYWORDS = (
    "brute-force", "sqlmap", "nmap", "nikto", "gobuster",
    "null scan", "fin scan", "xmas scan", "time-based blind",
)

# Deduplicación de alertas críticas para no repetir el mismo aviso en bucle
CRITICAL_DEDUPE_TTL = 30
_last_critical_sent = {}


def is_critical(signature):
    sig_lower = signature.lower()
    return any(k in sig_lower for k in CRITICAL_KEYWORDS)


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "text": message},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"Error enviando mensaje Telegram: {e}")


def flush_window(alert_counter, window_start):
    total = sum(alert_counter.values())
    if total >= ALERT_THRESHOLD:
        msg = f"⚠️ Suricata: {total} alertas en los últimos {TIME_WINDOW}s:\n"
        for sig, count in alert_counter.most_common(10):
            msg += f"  • {sig}: {count}\n"
        send_telegram_message(msg)
    alert_counter.clear()


def wait_for_log(path, retries=30, delay=2):
    for _ in range(retries):
        try:
            open(path).close()
            return
        except FileNotFoundError:
            print(f"Esperando a que exista {path}...")
            time.sleep(delay)
    raise RuntimeError(f"Log file {path} not available after {retries * delay}s")


def monitor_log():
    wait_for_log(LOG_FILE)
    alert_counter = Counter()
    window_start = time.time()

    with open(LOG_FILE, "r") as f:
        f.seek(0, 2)  # posicionarse al final del fichero
        while True:
            line = f.readline()

            # Vaciar la ventana en cada iteración, no solo al llegar una línea nueva
            now = time.time()
            if now - window_start >= TIME_WINDOW:
                flush_window(alert_counter, window_start)
                window_start = now

            if not line:
                time.sleep(0.5)
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            if data.get("event_type") == "alert":
                signature = data.get("alert", {}).get("signature", "unknown")
                alert_counter[signature] += 1

                if is_critical(signature):
                    src = data.get("src_ip", "?")
                    dst = data.get("dest_ip", "?")
                    dport = data.get("dest_port", "?")
                    key = f"{signature}:{src}"
                    last_sent = _last_critical_sent.get(key, 0)
                    if now - last_sent > CRITICAL_DEDUPE_TTL:
                        _last_critical_sent[key] = now
                        send_telegram_message(
                            f"🚨 Suricata: {signature}\n"
                            f"  Origen: {src} → {dst}:{dport}"
                        )


if __name__ == "__main__":
    monitor_log()
