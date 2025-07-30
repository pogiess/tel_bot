# config.py

# Telegram Bot
BOT_TOKEN    = "7956961094:AAGgTQOHWH7hSVEBvJLc4iPOsiE23vydB3g"
CHANNEL_NAME = "@pographel"

# Binance API (optional if only public endpoints)
BINANCE_API_KEY    = "YOUR_BINANCE_API_KEY"
BINANCE_API_SECRET = "YOUR_BINANCE_SECRET"

# Trading Settings
EXCHANGE          = "binance"
SYMBOLS           = ["BTC/USDT", "ETH/USDT"]    # adjust your pairs
TIMEFRAME         = "1h"                       # e.g., '1m', '5m', '1h', '1d'
LIMIT             = 100                        # number of candles to fetch

# Indicator Parameters
RSI_PERIOD        = 14
RSI_OVERSOLD      = 30
RSI_OVERBOUGHT    = 70

EMA_SHORT_PERIOD  = 12
EMA_LONG_PERIOD   = 26

MACD_FAST_PERIOD  = 12
MACD_SLOW_PERIOD  = 26
MACD_SIGNAL_PERIOD= 9