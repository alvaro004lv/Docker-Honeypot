import os
import requests
import time
from threading import Thread

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['TELEGRAM_CHAT_ID']

# Ficheros cuyo acceso dispara una alerta (señal de que alguien ha encontrado credenciales)
SMB_BAIT_FILES = [
    'tunnel.sh',
    'remote_access.txt',
    'WiFi_Credentials.txt',
    'Software_Licenses.txt',
]


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar mensaje de Telegram: {e}")


def tail_file(path, retries=30, delay=2):
    for _ in range(retries):
        try:
            f = open(path, 'r')
            f.seek(0, 2)
            return f
        except FileNotFoundError:
            time.sleep(delay)
    raise RuntimeError(f"Log file {path} not found after waiting")


def monitor_ssh_logs():
    log_file = '/var/log/ssh/sshd.log'
    f = tail_file(log_file)
    while True:
        line = f.readline()
        if not line:
            time.sleep(1)
            continue
        if "Failed password" in line:
            send_telegram_message('🔴 Intento SSH fallido:\n' + line.strip())
        elif "Accepted password" in line or "Accepted publickey" in line:
            send_telegram_message('🟢 Acceso SSH exitoso:\n' + line.strip())
        elif "Disconnected from user" in line:
            send_telegram_message('⚪ Sesión SSH terminada:\n' + line.strip())


def monitor_smb_logs():
    log_file = '/var/log/samba/log.gateway'
    f = tail_file(log_file)
    while True:
        line = f.readline()
        if not line:
            time.sleep(1)
            continue
        line_lower = line.lower()
        for bait in SMB_BAIT_FILES:
            if bait.lower() in line_lower and "opened file" in line_lower:
                send_telegram_message(
                    f'📂 Acceso a fichero sensible en SMB: {bait}\n' + line.strip()
                )
                break


if __name__ == "__main__":
    ssh_thread = Thread(target=monitor_ssh_logs, daemon=True)
    smb_thread = Thread(target=monitor_smb_logs, daemon=True)

    ssh_thread.start()
    smb_thread.start()

    ssh_thread.join()
    smb_thread.join()
