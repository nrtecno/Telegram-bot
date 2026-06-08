from flask import Flask, request, jsonify
import telebot
import os
import sys
import logging
import json

# ========== LOGGING ==========
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========== FLASK APP ==========
app = Flask(__name__)

# ========== TOKEN FROM ENV VAR ==========
TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    logger.error("BOT_TOKEN environment variable not set!")
    bot = None
else:
    try:
        bot = telebot.TeleBot(TOKEN)
        bot_info = bot.get_me()
        logger.info(f"✅ Bot connected: @{bot_info.username}")
    except Exception as e:
        logger.error(f"Bot init failed: {e}")
        bot = None

# ========== BOT HANDLERS ==========
if bot:
    @bot.message_handler(commands=['start'])
    def start_handler(message):
        try:
            user_name = message.from_user.first_name
            logger.info(f"📨 /start from {user_name} (id: {message.chat.id})")
            bot.reply_to(message, f"✅ Hello {user_name}! Bot is working.\n\nSend me any URL.")
        except Exception as e:
            logger.error(f"Start handler error: {e}")

    @bot.message_handler(func=lambda m: True)
    def url_handler(message):
        try:
            text = message.text.strip()
            logger.info(f"📨 Message: {text[:50]}")
            if text.startswith(('http://', 'https://')):
                bot.reply_to(message, f"✅ URL received:\n{text}")
            else:
                bot.reply_to(message, "❌ Send a valid URL starting with http:// or https://")
        except Exception as e:
            logger.error(f"Message handler error: {e}")

# ========== WEBHOOK ROUTE ==========
@app.route('/webhook', methods=['POST'])
def webhook():
    if bot is None:
        logger.error("Bot not initialized")
        return jsonify({"status": "error"}), 500
    
    try:
        json_str = request.get_data().decode('UTF-8')
        logger.info(f"📨 Webhook received (length: {len(json_str)})")
        
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        
        logger.info("✅ Update processed successfully")
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return jsonify({"status": "error"}), 500

# ========== HEALTH CHECK ==========
@app.route('/', methods=['GET'])
def home():
    return "Bot is alive!"

# ========== MAIN ==========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🚀 Starting Flask app on port {port}")
    
    if bot and os.environ.get("RENDER_EXTERNAL_URL"):
        webhook_url = f"{os.environ.get('RENDER_EXTERNAL_URL')}/webhook"
        try:
            bot.remove_webhook()
            bot.set_webhook(url=webhook_url)
            logger.info(f"✅ Webhook set to {webhook_url}")
        except Exception as e:
            logger.error(f"Webhook set error: {e}")
    
    app.run(host='0.0.0.0', port=port)
