# telegram_bot.py

from telegram import Bot
from config import BOT_TOKEN, CHANNEL_NAME

bot = Bot(token=BOT_TOKEN)

def send_signal(symbol: str, signal: str, rsi_value: float):
    text = f"Signal for {symbol}:\n• Action: {signal}\n• RSI: {rsi_value:.2f}"
    bot.send_message(chat_id=CHANNEL_NAME, text=text)