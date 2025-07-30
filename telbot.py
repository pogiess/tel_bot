import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiohttp
import numpy as np
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
import json
import os
import signal
import sys

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramCryptoBot:
    def __init__(self, bot_token: str, channel_id: str):
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.application = None
        self.analysis_cache = {}
        self.watchlist = ['BTC', 'ETH', 'ADA', 'SOL', 'DOGE', 'MATIC', 'DOT', 'LINK']
        
    async def fetch_crypto_data(self, symbol: str, days: int = 30) -> Optional[Dict]:
        """
        Fetch real cryptocurrency data from CoinGecko API
        """
        try:
            url = f"https://api.coingecko.com/api/v3/coins/{symbol.lower()}/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': days,
                'interval': 'hourly' if days <= 30 else 'daily'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'prices': [price[1] for price in data['prices']],
                            'volumes': [volume[1] for volume in data['total_volumes']],
                            'market_caps': [cap[1] for cap in data['market_caps']]
                        }
                    else:
                        logger.error(f"Failed to fetch data for {symbol}: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return None

    def calculate_technical_indicators(self, prices: List[float]) -> Dict:
        """Calculate technical indicators"""
        if len(prices) < 20:
            return {}
            
        prices_array = np.array(prices)
        
        # Moving Averages
        sma_7 = np.mean(prices_array[-7:])
        sma_14 = np.mean(prices_array[-14:])
        sma_30 = np.mean(prices_array[-30:]) if len(prices) >= 30 else None
        
        # EMA calculation
        def calculate_ema(data, period):
            multiplier = 2 / (period + 1)
            ema = [data[0]]
            for i in range(1, len(data)):
                ema.append((data[i] * multiplier) + (ema[i-1] * (1 - multiplier)))
            return ema[-1]
        
        ema_12 = calculate_ema(prices, 12)
        ema_26 = calculate_ema(prices, 26)
        
        # RSI Calculation
        def calculate_rsi(prices, period=14):
            if len(prices) < period + 1:
                return 50
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])
            
            if avg_loss == 0:
                return 100
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        
        rsi = calculate_rsi(prices_array)
        
        # MACD
        macd_line = ema_12 - ema_26
        macd_signal = calculate_ema([macd_line] * 9, 9)  # Simplified signal line
        
        # Price change percentages
        price_change_24h = ((prices[-1] - prices[-24]) / prices[-24] * 100) if len(prices) >= 24 else 0
        price_change_7d = ((prices[-1] - prices[-168]) / prices[-168] * 100) if len(prices) >= 168 else 0
        
        return {
            'sma_7': sma_7,
            'sma_14': sma_14,
            'sma_30': sma_30,
            'ema_12': ema_12,
            'ema_26': ema_26,
            'rsi': rsi,
            'macd': macd_line,
            'macd_signal': macd_signal,
            'current_price': prices[-1],
            'price_change_24h': price_change_24h,
            'price_change_7d': price_change_7d
        }

    def analyze_signals(self, indicators: Dict, volumes: List[float]) -> Dict:
        """Analyze trading signals"""
        signals = []
        score = 0
        
        # Moving Average Signals
        if indicators['sma_7'] > indicators['sma_14']:
            signals.append("📈 Short-term bullish (7>14 SMA)")
            score += 1
        else:
            signals.append("📉 Short-term bearish (7<14 SMA)")
            score -= 1
            
        if indicators['sma_30'] and indicators['sma_14'] > indicators['sma_30']:
            signals.append("🚀 Medium-term bullish (14>30 SMA)")
            score += 1
        elif indicators['sma_30']:
            signals.append("⬇️ Medium-term bearish (14<30 SMA)")
            score -= 1
        
        # RSI Signals
        rsi = indicators['rsi']
        if rsi < 30:
            signals.append("💎 RSI Oversold - Potential Buy Zone")
            score += 2
        elif rsi > 70:
            signals.append("⚠️ RSI Overbought - Potential Sell Zone")
            score -= 2
        elif 45 <= rsi <= 55:
            signals.append("⚖️ RSI Neutral")
        
        # MACD Signals
        if indicators['macd'] > indicators['macd_signal']:
            signals.append("✅ MACD Bullish Cross")
            score += 1
        else:
            signals.append("❌ MACD Bearish Cross")
            score -= 1
        
        # Volume Analysis
        if len(volumes) >= 7:
            recent_vol = np.mean(volumes[-7:])
            older_vol = np.mean(volumes[-14:-7]) if len(volumes) >= 14 else recent_vol
            
            if recent_vol > older_vol * 1.5:
                signals.append("📊 High Volume Surge")
                score += 1
        
        # Determine overall signal
        if score >= 3:
            overall = "STRONG BUY 🟢"
            emoji = "🚀"
        elif score >= 1:
            overall = "BUY 🟡"
            emoji = "📈"
        elif score <= -3:
            overall = "STRONG SELL 🔴"
            emoji = "📉"
        elif score <= -1:
            overall = "SELL 🟠"
            emoji = "⬇️"
        else:
            overall = "HOLD ⚪"
            emoji = "⚖️"
        
        return {
            'signals': signals,
            'score': score,
            'overall_signal': overall,
            'emoji': emoji,
            'confidence': min(abs(score) * 20, 100)  # Convert to percentage
        }

    async def analyze_cryptocurrency(self, symbol: str) -> Optional[Dict]:
        """Complete cryptocurrency analysis"""
        try:
            # Fetch market data
            market_data = await self.fetch_crypto_data(symbol)
            if not market_data:
                return None
            
            # Calculate indicators
            indicators = self.calculate_technical_indicators(market_data['prices'])
            if not indicators:
                return None
            
            # Analyze signals
            signal_analysis = self.analyze_signals(indicators, market_data['volumes'])
            
            # Calculate volatility
            prices = np.array(market_data['prices'])
            returns = np.diff(np.log(prices))
            volatility = np.std(returns) * np.sqrt(24) * 100  # Daily volatility %
            
            return {
                'symbol': symbol.upper(),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
                'price': indicators['current_price'],
                'price_change_24h': indicators['price_change_24h'],
                'price_change_7d': indicators['price_change_7d'],
                'rsi': indicators['rsi'],
                'signals': signal_analysis['signals'],
                'overall_signal': signal_analysis['overall_signal'],
                'emoji': signal_analysis['emoji'],
                'confidence': signal_analysis['confidence'],
                'volatility': volatility,
                'volume_24h': market_data['volumes'][-1] if market_data['volumes'] else 0
            }
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None

    def format_analysis_message(self, analysis: Dict) -> str:
        """Format analysis into Telegram message"""
        message = f"""
{analysis['emoji']} **{analysis['symbol']} ANALYSIS** {analysis['emoji']}

💰 **Price:** ${analysis['price']:.4f}
📊 **24h Change:** {analysis['price_change_24h']:.2f}%
📈 **7d Change:** {analysis['price_change_7d']:.2f}%
🎯 **RSI:** {analysis['rsi']:.1f}

🚨 **SIGNAL: {analysis['overall_signal']}**
🎲 **Confidence:** {analysis['confidence']}%

**📋 Technical Analysis:**
"""
        
        for signal in analysis['signals'][:4]:  # Show top 4 signals
            message += f"• {signal}\n"
        
        message += f"""
📊 **Volatility:** {analysis['volatility']:.2f}%
⏰ **Updated:** {analysis['timestamp']}

⚠️ *This is educational analysis only, not financial advice*
"""
        return message

    async def send_channel_update(self, message: str) -> bool:
        """Send message to Telegram channel"""
        try:
            await self.application.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode='Markdown'
            )
            return True
        except Exception as e:
            logger.error(f"Error sending message to channel: {e}")
            return False

    async def analyze_and_broadcast(self):
        """Analyze watchlist and broadcast to channel"""
        logger.info("Starting crypto analysis broadcast...")
        
        for symbol in self.watchlist:
            try:
                analysis = await self.analyze_cryptocurrency(symbol)
                if analysis:
                    message = self.format_analysis_message(analysis)
                    success = await self.send_channel_update(message)
                    
                    if success:
                        logger.info(f"Broadcasted analysis for {symbol}")
                    else:
                        logger.error(f"Failed to broadcast {symbol}")
                    
                    # Rate limiting - wait between messages
                    await asyncio.sleep(2)
                else:
                    logger.warning(f"Could not analyze {symbol}")
                    
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
        
        logger.info("Broadcast completed")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        message = """
🤖 **Crypto Analysis Bot Started!**

Available commands:
/analyze [SYMBOL] - Analyze specific crypto
/watchlist - Show current watchlist
/add [SYMBOL] - Add crypto to watchlist
/remove [SYMBOL] - Remove from watchlist
/broadcast - Manual broadcast to channel
/help - Show this help

🔄 Auto-analysis runs every 4 hours
📢 Updates sent to channel automatically
        """
        await update.message.reply_text(message, parse_mode='Markdown')

    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analyze command"""
        if not context.args:
            await update.message.reply_text("Please specify a cryptocurrency symbol: /analyze BTC")
            return
        
        symbol = context.args[0].upper()
        await update.message.reply_text(f"🔍 Analyzing {symbol}...")
        
        analysis = await self.analyze_cryptocurrency(symbol)
        if analysis:
            message = self.format_analysis_message(analysis)
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ Could not analyze {symbol}. Check the symbol and try again.")

    async def watchlist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current watchlist"""
        message = "📋 **Current Watchlist:**\n\n"
        for i, symbol in enumerate(self.watchlist, 1):
            message += f"{i}. {symbol}\n"
        message += f"\n📊 Total: {len(self.watchlist)} cryptocurrencies"
        await update.message.reply_text(message, parse_mode='Markdown')

    async def add_to_watchlist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add crypto to watchlist"""
        if not context.args:
            await update.message.reply_text("Please specify a symbol: /add BTC")
            return
        
        symbol = context.args[0].upper()
        if symbol not in self.watchlist:
            self.watchlist.append(symbol)
            await update.message.reply_text(f"✅ Added {symbol} to watchlist")
        else:
            await update.message.reply_text(f"ℹ️ {symbol} is already in watchlist")

    async def remove_from_watchlist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove crypto from watchlist"""
        if not context.args:
            await update.message.reply_text("Please specify a symbol: /remove BTC")
            return
        
        symbol = context.args[0].upper()
        if symbol in self.watchlist:
            self.watchlist.remove(symbol)
            await update.message.reply_text(f"❌ Removed {symbol} from watchlist")
        else:
            await update.message.reply_text(f"ℹ️ {symbol} is not in watchlist")

    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manual broadcast trigger"""
        await update.message.reply_text("🚀 Starting manual broadcast...")
        await self.analyze_and_broadcast()
        await update.message.reply_text("✅ Broadcast completed!")

    async def scheduled_broadcast(self, context: ContextTypes.DEFAULT_TYPE):
        """Scheduled broadcast function"""
        await self.analyze_and_broadcast()

    def setup_handlers(self):
        """Setup command handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("analyze", self.analyze_command))
        self.application.add_handler(CommandHandler("watchlist", self.watchlist_command))
        self.application.add_handler(CommandHandler("add", self.add_to_watchlist_command))
        self.application.add_handler(CommandHandler("remove", self.remove_from_watchlist_command))
        self.application.add_handler(CommandHandler("broadcast", self.broadcast_command))
        self.application.add_handler(CommandHandler("help", self.start_command))

    async def test_bot_connection(self) -> bool:
        """Test if bot token is valid"""
        try:
            from telegram import Bot
            bot = Bot(token=self.bot_token)
            me = await bot.get_me()
            logger.info(f"✅ Bot connected successfully: @{me.username}")
            return True
        except Exception as e:
            logger.error(f"❌ Bot connection failed: {e}")
            return False

    async def test_channel_access(self) -> bool:
        """Test if bot can access the channel"""
        try:
            from telegram import Bot
            bot = Bot(token=self.bot_token)
            chat = await bot.get_chat(self.channel_id)
            logger.info(f"✅ Channel access confirmed: {chat.title}")
            return True
        except Exception as e:
            logger.error(f"❌ Channel access failed: {e}")
            logger.error("Make sure:")
            logger.error("1. Bot is added to the channel as admin")
            logger.error("2. Channel ID/username is correct")
            return False

    def setup_scheduled_jobs(self):
        """Setup scheduled jobs - now handled by schedule_broadcasts method"""
        pass

    async def run_bot(self):
        """Run the Telegram bot with improved compatibility"""
        try:
            # Test bot connection first
            logger.info("Testing bot connection...")
            if not await self.test_bot_connection():
                return
            
            logger.info("Testing channel access...")
            if not await self.test_channel_access():
                return
            
            # Create application with proper settings
            builder = Application.builder()
            builder.token(self.bot_token)
            builder.connect_timeout(30.0)
            builder.read_timeout(30.0)
            builder.write_timeout(30.0)
            builder.pool_timeout(30.0)
            
            self.application = builder.build()
            
            # Setup handlers
            self.setup_handlers()
            
            logger.info("Initializing bot...")
            await self.application.initialize()
            
            logger.info("Starting bot...")
            await self.application.start()
            
            # Setup scheduled job manually instead of using job_queue
            asyncio.create_task(self.schedule_broadcasts())
            
            logger.info("Starting polling...")
            # Use a simpler polling approach
            await self.application.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES
            )
            
            logger.info("✅ Bot is running successfully!")
            logger.info("Send /start to your bot to test it")
            logger.info("Press Ctrl+C to stop")
            
            # Setup signal handlers for graceful shutdown
            def signal_handler(signum, frame):
                logger.info("Received shutdown signal...")
                asyncio.create_task(self.shutdown_bot())
            
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            
            # Keep the bot running
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            await self.shutdown_bot()
        except Exception as e:
            logger.error(f"Error running bot: {e}")
            import traceback
            traceback.print_exc()
            await self.shutdown_bot()

    async def shutdown_bot(self):
        """Gracefully shutdown the bot"""
        try:
            if self.application:
                logger.info("Shutting down bot...")
                if hasattr(self.application, 'updater') and self.application.updater:
                    if hasattr(self.application.updater, 'stop'):
                        await self.application.updater.stop()
                
                if hasattr(self.application, 'stop'):
                    await self.application.stop()
                
                if hasattr(self.application, 'shutdown'):
                    await self.application.shutdown()
                
                logger.info("Bot shut down successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            sys.exit(0)

    async def schedule_broadcasts(self):
        """Manual scheduling instead of job_queue"""
        # Wait 1 minute before first broadcast
        await asyncio.sleep(60)
        
        while True:
            try:
                logger.info("Running scheduled broadcast...")
                await self.analyze_and_broadcast()
                logger.info("Scheduled broadcast completed")
                
                # Wait 4 hours (14400 seconds) before next broadcast
                await asyncio.sleep(14400)
                
            except Exception as e:
                logger.error(f"Error in scheduled broadcast: {e}")
                # Wait 30 minutes before retrying
                await asyncio.sleep(1800)

# Main execution
async def main():
    # Configuration - Replace with your actual values
    BOT_TOKEN = "7956961094:AAGgTQOHWH7hSVEBvJLc4iPOsiE23vydB3g"  # Get from @BotFather
    CHANNEL_ID = "@pographel"  # Your channel username or ID
    
    # Validate configuration
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ERROR: Please set your BOT_TOKEN in the main() function")
        print("Get your bot token from @BotFather on Telegram")
        print("\nExample:")
        print('BOT_TOKEN = "1234567890:AABBCCDDEEFFgghhiijjkkllmmnnoo"')
        return
    
    if CHANNEL_ID == "@your_channel_name":
        print("❌ ERROR: Please set your CHANNEL_ID in the main() function")
        print("Use your channel username like @mychannel or chat ID like -1001234567890")
        print("\nExample:")
        print('CHANNEL_ID = "@crypto_signals"')
        return
    
    print("🚀 Starting Telegram Crypto Bot...")
    print(f"📢 Channel: {CHANNEL_ID}")
    print("📋 Required packages: python-telegram-bot>=20.0 aiohttp numpy")
    print("\nIf you get errors, run:")
    print("pip install --upgrade python-telegram-bot aiohttp numpy")
    print("\nPress Ctrl+C to stop the bot")
    
    # Create and run bot
    bot = TelegramCryptoBot(BOT_TOKEN, CHANNEL_ID)
    
    try:
        await bot.run_bot()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        print("\nCommon fixes:")
        print("1. Make sure your bot token is correct")
        print("2. Add your bot as admin to the channel")
        print("3. Check your internet connection")
        print("4. Update python-telegram-bot: pip install --upgrade python-telegram-bot")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())