#!/usr/bin/env python3
"""
TradingView to Telegram Bot
Receives webhook signals from TradingView and sends notifications to Telegram channel
"""

import os
import logging
from datetime import datetime
from typing import Dict, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from telegram import Bot
from telegram.error import TelegramError
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="TradingView Telegram Bot")

# Configuration from environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID', '')
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'your-secret-key')

# Initialize Telegram Bot
telegram_bot: Optional[Bot] = None

# Track position states per symbol
position_states: Dict[str, Dict] = {}


def init_telegram_bot():
    """Initialize Telegram bot instance"""
    global telegram_bot
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return False
    
    try:
        telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)
        logger.info("Telegram bot initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Telegram bot: {e}")
        return False


async def send_telegram_message(message: str, parse_mode: str = 'HTML') -> bool:
    """Send message to Telegram channel"""
    if not telegram_bot:
        logger.error("Telegram bot not initialized")
        return False
    
    try:
        await telegram_bot.send_message(
            chat_id=TELEGRAM_CHANNEL_ID,
            text=message,
            parse_mode=parse_mode
        )
        logger.info(f"Message sent to Telegram channel {TELEGRAM_CHANNEL_ID}")
        return True
    except TelegramError as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


def format_entry_signal(data: Dict) -> str:
    """Format entry signal notification"""
    signal_type = data.get('signal_type', 'unknown')
    direction = "🟢 LONG" if 'long' in signal_type.lower() else "🔴 SHORT"
    
    symbol = data.get('symbol', 'UNKNOWN')
    timeframe = data.get('timeframe', '7m')
    price = data.get('price', 0)
    momentum = data.get('momentum', 0)
    vwap = data.get('vwap', 0)
    timestamp = data.get('timestamp', datetime.utcnow().isoformat())
    
    message = f"""
{direction} ВХОД В ПОЗИЦИЮ

<b>Символ:</b> {symbol}
<b>Таймфрейм:</b> {timeframe}
<b>Цена:</b> ${price:.6f}

📊 <b>Индикаторы:</b>
• Momentum: {momentum:.2f} {'(ниже -5.1)' if momentum < -5.1 else '(выше +5.1)'}
• VWAP: ${vwap:.6f}

⏰ <b>Время:</b> {timestamp}

<i>Начат набор позиции. Ожидайте уведомление с TP/SL...</i>
"""
    return message.strip()


def format_exit_signal(data: Dict) -> str:
    """Format exit signal with TP/SL notification"""
    symbol = data.get('symbol', 'UNKNOWN')
    direction = data.get('direction', 'LONG')
    entry_price = data.get('entry_price', 0)
    tp_price = data.get('tp_price', 0)
    sl_price = data.get('sl_price', 0)
    momentum = data.get('momentum', 0)
    timestamp = data.get('timestamp', datetime.utcnow().isoformat())
    
    # Calculate risk/reward ratio
    if direction.upper() == 'LONG':
        risk = abs(entry_price - sl_price)
        reward = abs(tp_price - entry_price)
    else:
        risk = abs(sl_price - entry_price)
        reward = abs(entry_price - tp_price)
    
    rr_ratio = reward / risk if risk > 0 else 0
    
    direction_emoji = "🟢" if direction.upper() == 'LONG' else "🔴"
    
    message = f"""
{direction_emoji} ПАРАМЕТРЫ ПОЗИЦИИ

<b>Символ:</b> {symbol}
<b>Направление:</b> {direction.upper()}
<b>Статус:</b> Набор позиции завершён

🎯 <b>Take Profit:</b> ${tp_price:.6f} (VWAP)
🛡 <b>Stop Loss:</b> ${sl_price:.6f} (ATR)

📊 <b>Анализ:</b>
• Momentum: {momentum:.2f} (вышел из зоны)
• Risk/Reward: 1:{rr_ratio:.2f}
• Плечо: 5x

⏰ <b>Время:</b> {timestamp}
"""
    return message.strip()


def format_update_signal(data: Dict) -> str:
    """Format position update notification"""
    symbol = data.get('symbol', 'UNKNOWN')
    update_type = data.get('update_type', 'info')
    message_text = data.get('message', '')
    price = data.get('price', 0)
    timestamp = data.get('timestamp', datetime.utcnow().isoformat())
    
    emoji = "ℹ️"
    if update_type == 'warning':
        emoji = "⚠️"
    elif update_type == 'success':
        emoji = "✅"
    elif update_type == 'error':
        emoji = "❌"
    
    message = f"""
{emoji} ОБНОВЛЕНИЕ ПОЗИЦИИ

<b>Символ:</b> {symbol}
<b>Цена:</b> ${price:.6f}

{message_text}

⏰ <b>Время:</b> {timestamp}
"""
    return message.strip()


@app.on_event("startup")
async def startup_event():
    """Initialize bot on startup"""
    logger.info("Starting TradingView Telegram Bot...")
    if init_telegram_bot():
        logger.info("Bot initialized successfully")
        # Send startup notification
        try:
            await send_telegram_message(
                "🤖 <b>Бот запущен</b>\n\nМониторинг сигналов TradingView активирован."
            )
        except Exception as e:
            logger.error(f"Failed to send startup message: {e}")
    else:
        logger.error("Failed to initialize bot")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "TradingView Telegram Bot",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    bot_status = "ok" if telegram_bot else "error"
    return {
        "status": "healthy",
        "telegram_bot": bot_status,
        "active_positions": len(position_states)
    }


@app.post("/webhook")
async def webhook_handler(request: Request):
    """Handle incoming webhooks from TradingView"""
    try:
        # Verify webhook secret
        auth_header = request.headers.get('Authorization', '')
        if auth_header != f"Bearer {WEBHOOK_SECRET}":
            logger.warning("Unauthorized webhook attempt")
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        # Parse webhook payload
        payload = await request.json()
        logger.info(f"Received webhook: {payload}")
        
        # Extract signal information
        signal_type = payload.get('signal_type', '')
        symbol = payload.get('symbol', '')
        
        # Process signal based on type
        if 'entry' in signal_type.lower():
            # Entry signal - start position accumulation
            message = format_entry_signal(payload)
            await send_telegram_message(message)
            
            # Store position state
            position_states[symbol] = {
                'status': 'accumulating',
                'entry_time': datetime.utcnow().isoformat(),
                'entry_price': payload.get('price', 0),
                'direction': 'LONG' if 'long' in signal_type.lower() else 'SHORT'
            }
            
        elif 'exit' in signal_type.lower():
            # Exit signal - position accumulated, send TP/SL
            if symbol in position_states:
                # Merge position state with payload
                payload['direction'] = position_states[symbol].get('direction', 'LONG')
                payload['entry_price'] = position_states[symbol].get('entry_price', 0)
            
            message = format_exit_signal(payload)
            await send_telegram_message(message)
            
            # Update position state
            if symbol in position_states:
                position_states[symbol]['status'] = 'active'
                position_states[symbol]['tp_price'] = payload.get('tp_price', 0)
                position_states[symbol]['sl_price'] = payload.get('sl_price', 0)
        
        elif 'update' in signal_type.lower():
            # General update notification
            message = format_update_signal(payload)
            await send_telegram_message(message)
        
        else:
            logger.warning(f"Unknown signal type: {signal_type}")
        
        return JSONResponse(
            status_code=200,
            content={"status": "success", "message": "Webhook processed"}
        )
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/test")
async def test_notification():
    """Test endpoint to send a test notification"""
    test_message = """
🧪 <b>ТЕСТОВОЕ УВЕДОМЛЕНИЕ</b>

Бот работает корректно и готов принимать сигналы от TradingView.

⏰ {time}
""".format(time=datetime.utcnow().isoformat())
    
    success = await send_telegram_message(test_message)
    
    if success:
        return {"status": "success", "message": "Test notification sent"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send test notification")


if __name__ == "__main__":
    # Run the server
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(
        "bot:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
