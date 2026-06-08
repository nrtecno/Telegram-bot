from flask import Flask, request, jsonify
import telebot
import os

app = Flask(__name__)

# Environment variable से token लो (सुरक्षित)
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise Exception("BOT_TOKEN environment variable not set!")

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✅ बॉट चल गया! कोई URL भेजो")

@bot.message_handler(func=lambda m: True)
def handle_url(message):
    url = message.text.strip()
    if url.startswith(("http://", "https://")):
        bot.reply_to(message, f"✅ लिंक मिल गया: {url}")
    else:
        bot.reply_to(message, "❌ सही URL भेजो")

@app.route('/webhook', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode('UTF-8'))
    bot.process_new_updates([update])
    return jsonify({"status": "ok"})

@app.route('/')
def home():
    return "Bot is alive!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
