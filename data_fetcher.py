# data_fetcher.py

import ccxt
import pandas as pd
from config import EXCHANGE, BINANCE_API_KEY, BINANCE_API_SECRET

def get_exchange():
    exchange_class = getattr(ccxt, EXCHANGE)
    exchange = exchange_class({
        'apiKey': BINANCE_API_KEY,
        'secret': BINANCE_API_SECRET,
        'enableRateLimit': True,
    })
    return exchange

def fetch_ohlcv(symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    exchange = get_exchange()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df.set_index('timestamp')