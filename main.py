# main.py

import time
from apscheduler.schedulers.blocking import BlockingScheduler
from config import SYMBOLS, TIMEFRAME, LIMIT
from data_fetcher import fetch_ohlcv
from signal_generator import generate_signal
from telegram_bot import send_signal

def job():
    for symbol in SYMBOLS:
        df = fetch_ohlcv(symbol, TIMEFRAME, LIMIT)
        signal, rsi_val = generate_signal(df)
        send_signal(symbol, signal, rsi_val)
        print(f"{symbol} -> {signal} (RSI {rsi_val:.2f})")

if __name__ == "__main__":
    scheduler = BlockingScheduler()
    # Schedule job every hour; adjust per your timeframe
    scheduler.add_job(job, 'cron', minute=1)  
    print("Bot started. Waiting for scheduled jobs...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")