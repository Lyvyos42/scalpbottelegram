# Add this at the top
import logging
logging.basicConfig(level=logging.INFO)

# Inside webhook function, add:
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        print("=== WEBHOOK RECEIVED ===")  # This shows in Render logs
        data = request.get_json()
        print(f"Data: {data}")
        # ... rest of your code
        from flask import Flask, request, jsonify
import os
import telegram
import json

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID')

bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

def format_message(data):
    """Format the message for Telegram based on the data structure."""
    # If data is a string, try to parse it as JSON
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            return data  # Return the string as is if it's not JSON
    
    # If data is a dictionary (JSON)
    if isinstance(data, dict):
        # Enhanced format from TradingView
        if 'pair' in data and 'action' in data:
            message = f"""
📊 {data.get('pair', 'N/A')} - {data.get('action', 'ALERT')}
Price: ${data.get('price', 'N/A')}
ADX: {data.get('adx_val', 'N/A')}
ATR: {data.get('atr', 'N/A')}
Reason: {data.get('reason', 'No reason')}
"""
            # Add SL and TP if present
            if 'sl_price' in data:
                message += f"SL: ${data['sl_price']}\n"
            if 'tp_price' in data:
                message += f"TP: ${data['tp_price']}\n"
            if 'position_size' in data:
                message += f"Qty: {data['position_size']}\n"
            
            # Add any extra fields (like avg_profit, etc.)
            extra_keys = [k for k in data.keys() if k not in ['pair', 'action', 'price', 'adx_val', 'atr', 'reason', 'sl_price', 'tp_price', 'position_size']]
            for key in extra_keys:
                message += f"{key}: {data[key]}\n"
            
            return message.strip()
        else:
            # If it's a dictionary but not in the expected format, convert to string
            return json.dumps(data, indent=2)
    else:
        # If it's not a string or dict, convert to string
        return str(data)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Get the data from TradingView
        data = request.get_json(force=True, silent=True)
        
        # If not JSON, try to get raw data
        if data is None:
            data = request.get_data(as_text=True)
        
        # Format the message
        message = format_message(data)
        
        # Send to Telegram
        bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message)
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/')
def home():
    return "TradingView Telegram Webhook Ready"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
