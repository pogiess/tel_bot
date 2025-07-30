# signal_generator.py

from config import RSI_OVERSOLD, RSI_OVERBOUGHT, EMA_SHORT_PERIOD, EMA_LONG_PERIOD, MACD_FAST_PERIOD, MACD_SLOW_PERIOD, MACD_SIGNAL_PERIOD
from indicators import ema, rsi, macd

def generate_signal(df):
    close = df['close']
    
    # EMA crossover
    ema_short = ema(close, EMA_SHORT_PERIOD)
    ema_long  = ema(close, EMA_LONG_PERIOD)
    cross_up   = (ema_short.iloc[-2] < ema_long.iloc[-2]) and (ema_short.iloc[-1] > ema_long.iloc[-1])
    cross_down = (ema_short.iloc[-2] > ema_long.iloc[-2]) and (ema_short.iloc[-1] < ema_long.iloc[-1])
    
    # RSI
    current_rsi = rsi(close, RSI_PERIOD).iloc[-1]
    
    # MACD
    macd_line, signal_line, hist = macd(close, MACD_FAST_PERIOD, MACD_SLOW_PERIOD, MACD_SIGNAL_PERIOD)
    macd_cross_up   = (macd_line.iloc[-2] < signal_line.iloc[-2]) and (macd_line.iloc[-1] > signal_line.iloc[-1])
    macd_cross_down = (macd_line.iloc[-2] > signal_line.iloc[-2]) and (macd_line.iloc[-1] < signal_line.iloc[-1])
    
    # Decision logic
    if cross_up and macd_cross_up and current_rsi < RSI_OVERBOUGHT:
        return "BUY", current_rsi
    if cross_down and macd_cross_down and current_rsi > RSI_OVERSOLD:
        return "SELL", current_rsi
    return "HOLD", current_rsi