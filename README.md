# Telegram Trading Bot - Deployment Guide

This bot receives trading signals from TradingView (via Webhook) and posts formatted alerts to a Telegram channel.

## 1. Project Setup
This project is ready to be uploaded to GitHub. It includes:
- `main.py`: The main application logic (Flask server).
- `requirements.txt`: Python dependencies.
- `Procfile`: Command for Railway to run the bot.
- `strategy.pine`: The updated TradingView strategy.

## 2. Deploy to Railway
1. **Push to GitHub**: Upload these files to a new GitHub repository.
2. **New Project on Railway**:
   - Go to [Railway.app](https://railway.app/).
   - Click "New Project" -> "Deploy from GitHub repo".
   - Select your repository.
3. **Set Environment Variables**:
   In your Railway project dashboard, go to the "Variables" tab and add:
   - `TELEGRAM_BOT_TOKEN`: Your bot token.
   - `TELEGRAM_CHAT_ID`: Your chat ID.
   - `PORT`: (Optional, Railway sets this automatically).
4. **Get Public URL**:
   - Go to the "Settings" tab in Railway.
   - Under "Networking", click "Generate Domain".
   - It will look like: `https://your-project-production.up.railway.app`.

## 3. Configure TradingView (CRITICAL STEP)
To get the alerts working, you must configure the **Webhook URL** in the **Alert Dialog**, not just the strategy inputs.

1. **Open TradingView**:
   - Paste the content of `strategy.pine` into the Pine Editor and click "Add to Chart".

2. **Create the Alert**:
   - Click the **Alerts** icon (clock on the right) or press `Alt+A`.
   - **Condition**: Select `AdaptiveMR` (the strategy name) from the dropdown.
   - **Order Fills**: You can uncheck this if you only want the custom alerts, but ensuring "Alert function calls" are active is key. Usually, selecting the Strategy automatically handles this.
   - **Expiration**: Set to "Open-ended" (if you have a paid plan) or the maximum allowed date.
   - **Alert Actions**:
     - **Check "Webhook URL"**.
     - **Paste your Railway URL** here: `https://your-project-production.up.railway.app/webhook`.
     - **IMPORTANT**: Ensure you add `/webhook` at the end of the URL.
   - **Message**: You can leave this default. The strategy code (`strategy.pine`) generates the correct JSON automatically using the `alert()` function.
   - Click **Create**.

## 4. Troubleshooting
- **Logs**: Check the "Deploy Logs" in Railway to see if signals are arriving (look for `Received webhook data`).
- **Telegram**: Ensure the bot is an Admin in the channel.
