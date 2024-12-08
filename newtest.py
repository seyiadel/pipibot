import MetaTrader5 as mt
import os
from dotenv import load_dotenv
import pytz
import datetime
import pandas as pd
import time
load_dotenv()

# mt.initialize()

def start_mt5_bot(account_number, password, symbol="XAUUSD", lot_size=0.01, sl_points=100, tp_points=200):
    # Initialize connection to MetaTrader 5
    if not mt.initialize():
        print("MT5 initialization failed")
        return
    
    if not mt.login(login=account_number, server="MetaQuotes-Demo", password=password):
        print("Login failed")
        mt.shutdown()
        return
    
    user_account = mt.account_info()
    print(f"Successfully logged in to account {user_account.login}")
    
    try:
        while True:
            # Fetch latest data
            rates = mt.copy_rates_from_pos(symbol, mt.TIMEFRAME_M15, 0, 100)  # Increased lookback period
            if rates is None:
                print("Failed to fetch rates")
                continue
            
            # Create DataFrame and calculate indicators
            rates_frame = pd.DataFrame(rates)
            rates_frame['time'] = pd.to_datetime(rates_frame['time'], unit='s')
            rates_frame.set_index('time', inplace=True)
            
            # Calculate multiple EMAs for trend confirmation
            rates_frame['EMA_10'] = rates_frame['close'].ewm(span=10, adjust=False).mean()
            rates_frame['EMA_20'] = rates_frame['close'].ewm(span=20, adjust=False).mean()
            rates_frame['EMA_50'] = rates_frame['close'].ewm(span=50, adjust=False).mean()
            
            # Calculate RSI for trend strength
            delta = rates_frame['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rates_frame['RSI'] = 100 - (100 / (1 + rs))
            
            # Calculate MACD for trend confirmation
            exp1 = rates_frame['close'].ewm(span=12, adjust=False).mean()
            exp2 = rates_frame['close'].ewm(span=26, adjust=False).mean()
            rates_frame['MACD'] = exp1 - exp2
            rates_frame['Signal_Line'] = rates_frame['MACD'].ewm(span=9, adjust=False).mean()
            
            # Analyze trend strength
            def analyze_trend_strength(row):
                strength = 0
                
                # EMA alignment check (trend structure)
                if row['EMA_10'] > row['EMA_20'] > row['EMA_50']:
                    strength += 1  # Bullish alignment
                elif row['EMA_10'] < row['EMA_20'] < row['EMA_50']:
                    strength -= 1  # Bearish alignment
                
                # RSI trend check
                if row['RSI'] > 50:
                    strength += 0.5
                elif row['RSI'] < 50:
                    strength -= 0.5
                
                # MACD confirmation
                if row['MACD'] > row['Signal_Line']:
                    strength += 0.5
                elif row['MACD'] < row['Signal_Line']:
                    strength -= 0.5
                
                return strength
            
            # Calculate trend strength for each row
            rates_frame['Trend_Strength'] = rates_frame.apply(analyze_trend_strength, axis=1)
            
            # Generate trading signals based on trend strength and confirmations
            def generate_signal(df):
                current_strength = df['Trend_Strength'].iloc[-1]
                prev_strength = df['Trend_Strength'].iloc[-2]
                
                # Check for strong trend confirmation
                if current_strength >= 1.5 and prev_strength < 1.5:
                    return 1  # Strong bullish signal
                elif current_strength <= -1.5 and prev_strength > -1.5:
                    return -1  # Strong bearish signal
                return 0
            
            # Generate signal for the latest candle
            latest_signal = generate_signal(rates_frame)
            
            # Execute trades based on signals
            if latest_signal != 0:
                # Additional trend confirmation
                recent_candles = rates_frame.tail(5)
                price_range = recent_candles['high'].max() - recent_candles['low'].min()
                atr = rates_frame['high'].subtract(rates_frame['low']).rolling(14).mean().iloc[-1]
                
                if latest_signal == 1:  # Bullish signal
                    # Check for pullback completion
                    if (rates_frame['close'].iloc[-1] > rates_frame['EMA_10'].iloc[-1] and 
                        rates_frame['RSI'].iloc[-1] > 40 and 
                        price_range < atr * 2):  # Controlled volatility
                        print(f"Strong bullish trend detected at {rates_frame.index[-1]}")
                        print(f"Trend Strength: {rates_frame['Trend_Strength'].iloc[-1]}")
                        # Uncomment to enable actual trading
                        # result = place_market_order(symbol, "BUY", lot_size, sl_points, tp_points)
                        # if result and result.retcode == mt.TRADE_RETCODE_DONE:
                        #     print(f"Buy order placed successfully: {result.order}")
                
                elif latest_signal == -1:  # Bearish signal
                    # Check for pullback completion
                    if (rates_frame['close'].iloc[-1] < rates_frame['EMA_10'].iloc[-1] and 
                        rates_frame['RSI'].iloc[-1] < 60 and 
                        price_range < atr * 2):  # Controlled volatility
                        print(f"Strong bearish trend detected at {rates_frame.index[-1]}")
                        print(f"Trend Strength: {rates_frame['Trend_Strength'].iloc[-1]}")
                        # Uncomment to enable actual trading
                        # result = place_market_order(symbol, "SELL", lot_size, sl_points, tp_points)
                        # if result and result.retcode == mt.TRADE_RETCODE_DONE:
                        #     print(f"Sell order placed successfully: {result.order}")
            
            # Position management
            positions = mt.positions_get(symbol=symbol)
            if positions:
                for position in positions:
                    current_profit = position.profit
                    position_type = position.type  # 0 for buy, 1 for sell
                    
                    # Dynamic position management based on trend strength
                    current_trend = rates_frame['Trend_Strength'].iloc[-1]
                    
                    # Close position if trend weakens significantly
                    if (position_type == 0 and current_trend < -1) or \
                       (position_type == 1 and current_trend > 1):
                        print(f"Closing position due to trend reversal. Profit: {current_profit}")
                        # Uncomment to enable actual trading
                        # close_position(position.ticket)
            
            # Display data
            # print("\nLatest market analysis:")
            # print(rates_frame[['close', 'EMA_10', 'EMA_20', 'EMA_50', 'RSI', 'MACD', 'Trend_Strength']].tail())
            
            # Wait before next iteration
            time.sleep(60 * 5)
            
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        mt.shutdown()
        print("MetaTrader 5 connection closed")



if __name__ == "__main__":
    account_number = os.getenv("ACCOUNT_NUMBER")
    password = os.getenv("PASSWORD")
    start_mt5_bot(5030889311, "PhS!0sIm")