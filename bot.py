from flask import Flask, request, jsonify
import os
import telegram
import logging

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get credentials
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

# Log environment status
logger.info(f"Bot token set: {'YES' if TELEGRAM_BOT_TOKEN else 'NO'}")
logger.info(f"Channel ID set: {'YES' if TELEGRAM_CHANNEL_ID else 'NO'}")

bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN) if TELEGRAM_BOT_TOKEN else None

@app.route('/webhook', methods=['POST'])
def webhook():
    logger.info("=== WEBHOOK RECEIVED ===")
    
    try:
        # Get data
        data = request.get_json()
        if data is None:
            data = request.get_data(as_text=True)
        
        logger.info(f"Received data: {data}")
        
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
            error_msg = "Missing Telegram credentials"
            logger.error(error_msg)
            return jsonify({'error': error_msg}), 500
        
        # Format message
        if isinstance(data, dict):
            pair = data.get('pair', 'Unknown')
            action = data.get('action', 'ALERT')
            price = data.get('price', 'N/A')
            reason = data.get('reason', 'No reason')
            
            message = f"""
📊 {action} - {pair}
Price: {price}
Reason: {reason}
"""
        else:
            message = str(data)
        
        # Send to Telegram
        logger.info(f"Sending to Telegram: {message}")
        bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message)
        logger.info("Message sent successfully")
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/')
def home():
    return "TradingView Telegram Webhook - Ready"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
