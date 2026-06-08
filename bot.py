from flask import Flask, request, jsonify
import telebot
import os
import sys
import logging
import json
import time

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    logger.error("BOT_TOKEN environment variable not set!")
    bot = None
else:
    try:
        bot = telebot.TeleBot(TOKEN)
        bot_info = bot.get_me()
        logger.info(f"Bot connected: @{bot_info.username}")
    except Exception as e:
        logger.error(f"Bot init failed: {e}")
        bot = None


def process_update(update):
    try:
        if hasattr(update, 'message') and update.message:
            msg = update.message
            text = msg.text if msg.text else ""
            chat_id = msg.chat.id
            user_name = msg.from_user.first_name
            
            logger.info(f"Message from {user_name}: {text}")
            
            if text == '/start':
                bot.send_message(chat_id, f"Hello {user_name}! Bot is working. Send me any URL.")
            elif text.startswith(('http://', 'https://')):
                bot.send_message(chat_id, f"URL received: {text}")
            else:
                bot.send_message(chat_id, "Send a valid URL starting with http:// or https://")
    except Exception as e:
        logger.error(f"Process update error: {e}")


@app.route('/webhook', methods=['POST'])
def webhook():
    if bot is None:
        return jsonify({"status": "error"}), 500
    
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        process_update(update)
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500


@app.route('/', methods=['GET'])
def home():
    return "Bot is alive!"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    
    if bot and os.environ.get("RENDER_EXTERNAL_URL"):
        webhook_url = f"{os.environ.get('RENDER_EXTERNAL_URL')}/webhook"
        try:
            bot.remove_webhook()
            time.sleep(1)
            bot.set_webhook(url=webhook_url)
            logger.info(f"Webhook set to {webhook_url}")
        except Exception as e:
            logger.error(f"Webhook error: {e}")
    
    app.run(host='0.0.0.0', port=port)
