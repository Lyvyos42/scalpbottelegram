from flask import Flask, request, jsonify
import os
import telegram
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Get credentials
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

# Log startup info
logger.info("=== BOT STARTING ===")
logger.info(f"Bot token available: {'YES' if TELEGRAM_BOT_TOKEN else 'NO'}")
logger.info(f"Channel ID: {TELEGRAM_CHANNEL_ID}")

if TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID:
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
else:
    bot = None
    logger.error("MISSING TELEGRAM CREDENTIALS!")

@app.route('/webhook', methods=['POST'])
def webhook():
    logger.info("=== WEBHOOK RECEIVED ===")
    
    try:
        # Get the data
        data = request.get_json()
        if data is None:
            raw_data = request.get_data(as_text=True)
            logger.info(f"Raw data received: {raw_data}")
            data = raw_data
        else:
            logger.info(f"JSON data received: {data}")
        
        # Check bot is configured
        if not bot:
            logger.error("Bot not configured - check environment variables")
            return jsonify({'error': 'Bot not configured'}), 500
        
        # Format message
        if isinstance(data, dict):
            pair = data.get('pair', 'Unknown')
            action = data.get('action', 'ALERT')
            price = data.get('price', 'N/A')
            reason = data.get('reason', 'No reason')
            
            message = f"""
📊 {action} - {pair}
💰 Price: {price}
📈 Reason: {reason}
🚀 Webhook received successfully!
"""
        else:
            message = f"📊 Alert received:\n{data}"
        
        # Send to Telegram
        logger.info(f"Sending to Telegram: {message[:100]}...")
        bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message)
        logger.info("✅ Message sent to Telegram successfully!")
        
        return jsonify({'status': 'success', 'received': data}), 200
        
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/')
def home():
    return "✅ TradingView → Telegram Webhook is RUNNING"

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port)
