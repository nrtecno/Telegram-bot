from flask import Flask, request, jsonify
import telebot
import os
import sys
import logging

# ========== LOGGING SETUP ==========
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ========== FLASK APP ==========
app = Flask(__name__)

# ========== ENVIRONMENT VARIABLE से TOKEN लो – HARDCODE नहीं ==========
TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    logger.error("BOT_TOKEN environment variable not set! Please set it in Render Dashboard.")
    bot = None
else:
    try:
        bot = telebot.TeleBot(TOKEN, parse_mode=None)
        bot_info = bot.get_me()
        logger.info(f"Bot connected successfully! Bot username: @{bot_info.username}")
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}")
        bot = None

# ========== HEALTH CHECK ==========
@app.route('/', methods=['GET'])
def home():
    return "Bot is alive!"

# ========== WEBHOOK ENDPOINT ==========
@app.route('/webhook', methods=['POST'])
def webhook():
    if bot is None:
        logger.error("Bot not initialized – check BOT_TOKEN environment variable")
        return jsonify({"status": "error", "message": "Bot not initialized"}), 500
    
    try:
        if request.headers.get('content-type') == 'application/json':
            json_str = request.get_data().decode('UTF-8')
            logger.info(f"Webhook received data")
            update = telebot.types.Update.de_json(json_str)
            bot.process_new_updates([update])
            return jsonify({"status": "ok"}), 200
        else:
            return jsonify({"status": "error"}), 403
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ========== BOT HANDLERS ==========
if bot:
    @bot.message_handler(commands=['start'])
    def handle_start(message):
        try:
            user_id = message.chat.id
            user_name = message.from_user.first_name
            logger.info(f"Start command from user {user_id} ({user_name})")
            bot.reply_to(message, f"✅ Hello {user_name}! Bot is working perfectly.\n\nSend me any URL.")
        except Exception as e:
            logger.error(f"Error in start handler: {e}")

    @bot.message_handler(func=lambda m: True)
    def handle_message(message):
        try:
            text = message.text.strip()
            logger.info(f"Message received: {text[:100]}")
            
            if text.startswith(("http://", "https://")):
                bot.reply_to(message, f"✅ URL received:\n{text}")
            else:
                bot.reply_to(message, "❌ Please send a valid URL starting with http:// or https://")
        except Exception as e:
            logger.error(f"Error in message handler: {e}")

# ========== SET WEBHOOK ON START ==========
def set_webhook():
    if bot is None:
        logger.error("Cannot set webhook – bot not initialized")
        return
    
    try:
        webhook_url = os.environ.get("RENDER_EXTERNAL_URL")
        if not webhook_url:
            logger.warning("RENDER_EXTERNAL_URL not set, webhook not configured")
            return
        
        webhook_url = f"{webhook_url}/webhook"
        logger.info(f"Setting webhook to: {webhook_url}")
        
        bot.remove_webhook()
        result = bot.set_webhook(url=webhook_url)
        
        if result:
            logger.info(f"Webhook set successfully")
        else:
            logger.error(f"Failed to set webhook")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")

# ========== MAIN ENTRY POINT ==========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Starting Flask app on port {port}")
    
    # Only set webhook if NOT in local development mode
    if not os.environ.get("FLASK_ENV") == "development" and bot:
        set_webhook()
    
    app.run(host='0.0.0.0', port=port)
