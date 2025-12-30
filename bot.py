from flask import Flask, request, jsonify
import os
import telegram
import logging

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None

@app.route('/webhook', methods=['POST'])
def webhook():
    logger.info("=== WEBHOOK CALLED ===")
    
    try:
        data = request.get_json()
        if not data:
            data = request.get_data(as_text=True)
            logger.info(f"Raw data: {data}")
        else:
            logger.info(f"JSON data: {data}")
        
        # Check if bot is configured
        if not bot:
            logger.error("Telegram bot not configured!")
            return jsonify({'error': 'Bot not configured'}), 500
        
        # Send test message
        message = f"Test alert: {data.get('pair', 'Unknown')} - {data.get('action', 'ALERT')}"
        bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message)
        logger.info("Message sent to Telegram")
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/')
def home():
    return "Webhook Ready - Debug Mode"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
