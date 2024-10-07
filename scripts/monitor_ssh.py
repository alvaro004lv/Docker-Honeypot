import requests
import time

TELEGRAM_TOKEN = 'YOUR_BOT_TOKEN' # change this with your bot token
CHAT_ID = 'YOUR_CHAT_ID' # change this with your telegram bot chat id

def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    data = {
        'chat_id': CHAT_ID,
        'text': message,
    }
    response = requests.post(url, data=data)
    return response

def monitor_logs():
    log_file = '/var/log/auth.log'
    with open(log_file, 'r') as f:
        f.seek(0, 2) 
        while True:
            line = f.readline()
            if not line:
                time.sleep(1)
                continue

            if "Failed password" in line:
                send_telegram_message('Alerta: Intento de acceso SSH fallido:\n' + line.strip())

            elif "Accepted password" in line or "Accepted publickey" in line:
                send_telegram_message('Alerta: Acceso SSH exitoso:\n' + line.strip())

if __name__ == "__main__":
    monitor_logs()