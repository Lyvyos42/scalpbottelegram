import time
import logging
import requests
import os
import sys
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

class MarketType(Enum):
    FOREX = "FOREX"
    CRYPTO = "CRYPTO"
    COMMODITIES = "COMMODITIES"
    INDICES = "INDICES"

class TimeFrame(Enum):
    M1 = "1M"
    M3 = "3M"
    M5 = "5M"
    M15 = "15M"
    M30 = "30M"
    H1 = "1H"
    H4 = "4H"
    D1 = "1D"

@dataclass
class MarketProfile:
    """Market-specific volatility and characteristics"""
    symbol: str
    market_type: MarketType
    spread: float
    pip_value: float = 10.0

class TelegramNotifier:
    """Handle Telegram notifications"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}/"
        
    def send_message(self, text: str, parse_mode: str = "HTML", disable_notification: bool = False):
        """Send message to Telegram"""
        try:
            url = f"{self.base_url}sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_notification": disable_notification
            }
            
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("Telegram message sent")
                return True
            else:
                logger.error(f"Failed to send Telegram message: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def send_trade_signal(self, trade_plan: Dict):
        """Send trade signal to Telegram"""
        try:
            symbol = trade_plan['symbol']
            direction = trade_plan['direction']
            entry = trade_plan['entry_price']
            sl = trade_plan['stop_loss']
            timeframe = trade_plan.get('timeframe', '5M')
            score = trade_plan.get('score', 0)
            pattern = trade_plan.get('pattern', '')
            session = trade_plan.get('session', '')
            
            symbol_upper = symbol.upper().replace("/", "")
            
            if "LONG" in direction.upper() or "BUY" in direction.upper():
                dir_emoji = "🟢"
                dir_text = "BUY / LONG"
                head_emoji = "🚀"
            else:
                dir_emoji = "🔴"
                dir_text = "SELL / SHORT"
                head_emoji = "📉"
            
            def fmt(price):
                if any(x in symbol_upper for x in ["XAU", "XAG"]):
                    return f"{price:.2f}"
                elif any(x in symbol_upper for x in ["BTC", "ETH"]):
                    return f"{price:.2f}"
                elif "JPY" in symbol_upper:
                    return f"{price:.3f}"
                return f"{price:.5f}"
            
            # Build TP block
            tp_block = ""
            tps = trade_plan.get('take_profits', [])
            for i, tp in enumerate(tps):
                price = tp.get('price', 0)
                rr = tp.get('rr_ratio', i+1)
                tp_block += f"{i+1}️⃣ <code>{fmt(price)}</code> ({rr}R)\n"
            
            # Score badge
            if score >= 85:
                score_badge = f"🔥🔥 {score}/100"
            elif score >= 70:
                score_badge = f"🔥 {score}/100"
            else:
                score_badge = f"✅ {score}/100"
            
            risk_pips = abs(entry - sl)
            if "XAU" in symbol_upper:
                risk_pips = risk_pips / 0.10
            
            msg = f"""<b>{head_emoji} SIGNAL: {symbol}</b>
{dir_emoji} <b>{dir_text}</b>

<b>Entry:</b> <code>{fmt(entry)}</code>
<b>Stop Loss:</b> <code>{fmt(sl)}</code>

<b>🎯 Targets:</b>
{tp_block}
<b>Score:</b> {score_badge}
<b>Pattern:</b> {pattern}
<b>Session:</b> {session}
<b>TF:</b> {timeframe}

<i>{datetime.now().strftime('%Y-%m-%d %H:%M')}</i>
#{symbol_upper} #{direction.split()[0]}"""
            return self.send_message(msg)
        except Exception as e:
            logger.error(f"Error in send_trade_signal: {e}")
            return False

    def send_profit_update(self, symbol: str, action: str, price: float):
        """Send TP hit notification"""
        try:
            # Determine TP Level
            if "TP1" in action:
                emoji = "💰"
                level = "TP1"
                comment = "First Target Hit!"
            elif "TP2" in action:
                emoji = "💰💰"
                level = "TP2"
                comment = "Second Target Hit! Move SL to Breakeven."
            elif "TP3" in action:
                emoji = "🚀🔥"
                level = "TP3 (FULL)"
                comment = "Final Target Hit! Trade Closed."
            else:
                emoji = "🔔"
                level = "UPDATE"
                comment = "Trade Update"

            message = f"""
<b>{emoji} PROFIT HIT: {symbol}</b>
━━━━━━━━━━━━━━━━━━━━
<b>🎯 Level:</b> {level}
<b>💵 Price:</b> <code>{price}</code>

<i>{comment}</i>
━━━━━━━━━━━━━━━━━━━━
#{symbol.replace('/', '')} #{level}
"""
            return self.send_message(message)
        except Exception as e:
            logger.error(f"Error creating profit update message: {e}")
            return False

class DynamicRiskManager:
    """Dynamic risk management with REALISTIC calculations"""
    
    def __init__(self):
        # REALISTIC stop loss in pips/points for each timeframe
        self.timeframe_stops = {
            TimeFrame.M1: {"pips": 2, "crypto_points": 5, "gold_points": 2},
            TimeFrame.M3: {"pips": 3, "crypto_points": 10, "gold_points": 3},
            TimeFrame.M5: {"pips": 5, "crypto_points": 15, "gold_points": 5},
            TimeFrame.M15: {"pips": 8, "crypto_points": 25, "gold_points": 8},
            TimeFrame.M30: {"pips": 12, "crypto_points": 40, "gold_points": 12},
            TimeFrame.H1: {"pips": 15, "crypto_points": 60, "gold_points": 15},
            TimeFrame.H4: {"pips": 25, "crypto_points": 100, "gold_points": 25},
            TimeFrame.D1: {"pips": 40, "crypto_points": 200, "gold_points": 40}
        }
        
        # Risk/Reward ratios for each timeframe
        self.timeframe_rr_ratios = {
            TimeFrame.M1: [1.0, 1.5, 2.0],
            TimeFrame.M3: [1.0, 2.0, 3.0],
            TimeFrame.M5: [1.5, 2.5, 3.5],
            TimeFrame.M15: [2.0, 3.0, 4.0],
            TimeFrame.M30: [2.0, 3.0, 4.0],
            TimeFrame.H1: [2.5, 3.5, 5.0],
            TimeFrame.H4: [3.0, 4.0, 6.0],
            TimeFrame.D1: [3.0, 5.0, 8.0]
        }
    
    def get_stop_distance(self, symbol: str, timeframe: TimeFrame) -> float:
        """Get realistic stop distance based on symbol and timeframe"""
        symbol_upper = symbol.upper().replace("/", "")
        config = self.timeframe_stops.get(timeframe, self.timeframe_stops[TimeFrame.M5])
        
        if "BTC" in symbol_upper or "ETH" in symbol_upper or "SOL" in symbol_upper:
            return config["crypto_points"]
        elif "XAU" in symbol_upper or "XAG" in symbol_upper:
            return config["gold_points"]
        else:
            return config["pips"]
    
    def calculate_pip_size(self, symbol: str) -> float:
        symbol_upper = symbol.upper().replace("/", "")
        
        if "JPY" in symbol_upper:
            return 0.01
        elif "XAU" in symbol_upper or "XAG" in symbol_upper:
            return 0.01
        elif "BTC" in symbol_upper:
            return 1.0
        elif "ETH" in symbol_upper:
            return 0.1
        elif "SOL" in symbol_upper:
            return 0.01
        else:
            return 0.0001
    
    def calculate_stop_loss(self, 
                           symbol: str,
                           entry_price: float,
                           direction: str,
                           timeframe: TimeFrame,
                           market_type: MarketType) -> Dict:
        
        stop_distance_units = self.get_stop_distance(symbol, timeframe)
        
        # Determine actual price distance
        if market_type == MarketType.CRYPTO or market_type == MarketType.COMMODITIES or market_type == MarketType.INDICES:
            stop_price_distance = stop_distance_units
            stop_pips = stop_distance_units 
        else:
            pip_size = self.calculate_pip_size(symbol)
            stop_price_distance = stop_distance_units * pip_size
            stop_pips = stop_distance_units
        
        if "SHORT" in direction.upper() or "SELL" in direction.upper():
            stop_price = entry_price + stop_price_distance
        else:
            stop_price = entry_price - stop_price_distance
        
        return {
            "stop_loss": stop_price,
            "stop_pips": round(stop_pips, 1),
            "stop_distance": stop_price_distance
        }
    
    def calculate_take_profits(self,
                              entry_price: float,
                              stop_pips: float,
                              direction: str,
                              timeframe: TimeFrame,
                              symbol: str,
                              market_type: MarketType) -> List[Dict]:
        
        rr_ratios = self.timeframe_rr_ratios.get(timeframe, [1.0, 2.0, 3.0])
        
        tp_levels = []
        for i, ratio in enumerate(rr_ratios):
            if market_type in [MarketType.CRYPTO, MarketType.COMMODITIES, MarketType.INDICES]:
                tp_distance = stop_pips * ratio
            else:
                pip_size = self.calculate_pip_size(symbol)
                tp_distance = stop_pips * ratio * pip_size
            
            if "SHORT" in direction.upper() or "SELL" in direction.upper():
                tp_price = entry_price - tp_distance
            else:
                tp_price = entry_price + tp_distance
            
            tp_levels.append({
                "level": i + 1,
                "price": tp_price,
                "pips": round(stop_pips * ratio, 1),
                "rr_ratio": ratio,
                "distance": tp_distance
            })
        
        return tp_levels

class TradingBot:
    """Trading bot with Webhook Support"""
    
    def __init__(self):
        # Read credentials from environment variables
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not self.telegram_token or not self.chat_id:
            logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set! Notifications will fail.")
        else:
            self.telegram = TelegramNotifier(self.telegram_token, self.chat_id)
            
        self.risk_manager = DynamicRiskManager()
        self.market_profiles = self.initialize_market_profiles()
    
    def initialize_market_profiles(self) -> Dict[str, MarketProfile]:
        return {
            "EURUSD": MarketProfile("EURUSD", MarketType.FOREX, 0.0001, 10.0),
            "GBPUSD": MarketProfile("GBPUSD", MarketType.FOREX, 0.00012, 10.0),
            "USDJPY": MarketProfile("USDJPY", MarketType.FOREX, 0.01, 9.27),
            "EURCAD": MarketProfile("EURCAD", MarketType.FOREX, 0.00015, 7.5),
            "BTCUSD": MarketProfile("BTCUSD", MarketType.CRYPTO, 5.0, 1.0),
            "ETHUSD": MarketProfile("ETHUSD", MarketType.CRYPTO, 0.5, 1.0),
            "SOLUSD": MarketProfile("SOLUSD", MarketType.CRYPTO, 0.1, 1.0),
            "XAUUSD": MarketProfile("XAUUSD", MarketType.COMMODITIES, 0.5, 1.0),
        }
    
    def get_market_profile(self, symbol: str) -> MarketProfile:
        symbol_clean = symbol.upper().replace("/", "")
        
        # Check explicit first
        if symbol_clean in self.market_profiles:
            return self.market_profiles[symbol_clean]
        
        # Auto-detect
        if any(crypto in symbol_clean for crypto in ["BTC", "ETH", "SOL", "DOGE", "ADA"]):
            return MarketProfile(symbol_clean, MarketType.CRYPTO, 1.0, 1.0)
        elif "XAU" in symbol_clean or "XAG" in symbol_clean or "OIL" in symbol_clean:
            return MarketProfile(symbol_clean, MarketType.COMMODITIES, 0.5, 1.0)
        elif "US30" in symbol_clean or "NAS100" in symbol_clean or "SPX" in symbol_clean:
            return MarketProfile(symbol_clean, MarketType.INDICES, 1.0, 1.0)
        else:
            return MarketProfile(symbol_clean, MarketType.FOREX, 0.0001, 10.0)
            
    def process_webhook(self, data: Dict) -> bool:
        """Process incoming webhook data"""
        try:
            logger.info(f"Received webhook: {data}")
            
            symbol = data.get('pair') or data.get('symbol') or "UNKNOWN"
            direction = data.get('action') or data.get('direction') or "UNKNOWN"
            
            # Handle TP/SL hit notifications
            if "TP" in direction.upper() or "_HIT" in direction.upper():
                price = float(data.get('price', 0))
                if self.telegram:
                    return self.telegram.send_profit_update(symbol, direction, price)
                return False
            
            if direction.upper() not in ["LONG", "SHORT", "BUY", "SELL"]:
                logger.info(f"Ignoring: {direction}")
                return False
            
            entry = float(data.get('price') or data.get('entry', 0))
            timeframe_str = data.get('timeframe', "5M")
            score = int(data.get('score') or data.get('ai_score', 0))
            pattern = data.get('pattern', '')
            session = data.get('session', '')
            
            # Check if TPs provided by Pine Script
            tp1 = data.get('tp1') or data.get('take_profit_1')
            tp2 = data.get('tp2') or data.get('take_profit_2')
            tp3 = data.get('tp3') or data.get('take_profit_3')
            sl = data.get('stop_loss')
            
            if tp1 and tp2 and tp3 and sl:
                # Use Pine Script provided values
                trade_plan = {
                    "symbol": symbol,
                    "direction": direction,
                    "timeframe": timeframe_str,
                    "entry_price": entry,
                    "stop_loss": float(sl),
                    "score": score,
                    "pattern": pattern,
                    "session": session,
                    "take_profits": [
                        {"price": float(tp1), "rr_ratio": 1.5},
                        {"price": float(tp2), "rr_ratio": 2.5},
                        {"price": float(tp3), "rr_ratio": 4.0}
                    ]
                }
            else:
                # Calculate TPs dynamically
                tf_map = {
                    "1": TimeFrame.M1, "3": TimeFrame.M3, "5": TimeFrame.M5,
                    "15": TimeFrame.M15, "30": TimeFrame.M30, "60": TimeFrame.H1,
                    "240": TimeFrame.H4, "D": TimeFrame.D1, "1D": TimeFrame.D1
                }
                tf = tf_map.get(timeframe_str.upper().replace("M","").replace("H",""), TimeFrame.M5)
                profile = self.get_market_profile(symbol)
                
                stop_data = self.risk_manager.calculate_stop_loss(
                    symbol, entry, direction, tf, profile.market_type
                )
                tp_levels = self.risk_manager.calculate_take_profits(
                    entry, stop_data["stop_pips"], direction, tf, symbol, profile.market_type
                )
                
                trade_plan = {
                    "symbol": symbol,
                    "direction": direction,
                    "timeframe": tf.value,
                    "entry_price": entry,
                    "stop_loss": stop_data["stop_loss"],
                    "score": score,
                    "pattern": pattern,
                    "session": session,
                    "take_profits": tp_levels
                }
            
            if self.telegram:
                return self.telegram.send_trade_signal(trade_plan)
            logger.error("Telegram not initialized")
            return False
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return False

# Initialize bot instance
bot = TradingBot()

@app.route('/')
def home():
    return "Trading Bot Active 🟢", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        logger.info(f"RAW PAYLOAD: {request.data}")
        logger.info(f"ContentType: {request.headers.get('Content-Type')}")
        
        # Force parsing as JSON even if Content-Type header is missing or wrong
        try:
            data = request.get_json(force=True, silent=True)
            if not data and request.data:
                # Fallback: try to parse raw data string manually
                import json
                data = json.loads(request.data.decode('utf-8'))
        except Exception:
            return jsonify({"error": "Invalid JSON format"}), 400
            
        if not data:
            return jsonify({"error": "No JSON data received"}), 400
            
        success = bot.process_webhook(data)
        
        if success:
            return jsonify({"status": "success", "message": "Signal processed"}), 200
        else:
            return jsonify({"status": "ignored", "message": "Signal ignored or failed"}), 200
            
    return jsonify({"error": "Method not allowed"}), 405

def main():
    # Only for local testing
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    main()
