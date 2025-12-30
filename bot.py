from flask import Flask, request, jsonify
import os
import telegram

app = Flask(__name__)

# Get credentials from Render environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

# Initialize bot
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        
        # Extract data from TradingView alert
        pair = data.get('pair', 'Unknown')
        action = data.get('action', 'ALERT')
        price = data.get('price', 'N/A')
        reason = data.get('reason', 'No reason')
        
        # Format message
        msg = f"""
📊 TradingView Alert
Pair: {pair}
Action: {action}
Price: ${price}
Reason: {reason}
"""
        
        # Send to Telegram
        bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=msg)
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error'}), 500

@app.route('/')
def home():
    return "Telegram Webhook Ready"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

