import MetaTrader5 as mt
import os
from dotenv import load_dotenv
import pytz
import datetime
import pandas as pd
import time
load_dotenv()

mt.initialize()

def place_market_order(symbol, order_type, lot_size, sl_points, tp_points):
    """
    Place a market order with stop loss and take profit
    """
    symbol_info = mt.symbol_info(symbol)
    if symbol_info is None:
        print(f"Symbol {symbol} not found")
        return None
    
    point = symbol_info.point
    price = mt.symbol_info_tick(symbol).ask if order_type == 'BUY' else mt.symbol_info_tick(symbol).bid
    
    request = {
        "action": mt.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": mt.ORDER_TYPE_BUY if order_type == 'BUY' else mt.ORDER_TYPE_SELL,
        "price": price,
        "sl": price - sl_points * point if order_type == 'BUY' else price + sl_points * point,
        "tp": price + tp_points * point if order_type == 'BUY' else price - tp_points * point,
        "deviation": 20,
        "magic": 234000,
        "comment": f"PipBot {order_type} order",
        "type_time": mt.ORDER_TIME_GTC,
        "type_filling": mt.ORDER_FILLING_IOC,
    }
    
    result = mt.order_send(request)
    return result


    
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
            rates = mt.copy_rates_from_pos(symbol, mt.TIMEFRAME_M15, 0, 60)
            if rates is None:
                print("Failed to fetch rates")
                continue
            
            # Create DataFrame and calculate indicators
            rates_frame = pd.DataFrame(rates)
            rates_frame['time'] = pd.to_datetime(rates_frame['time'], unit='s')
            rates_frame.set_index('time', inplace=True)
            
            # Calculate Median Price
            rates_frame['Median_Price'] = (rates_frame['high'] + rates_frame['low']) / 2
            
            # Calculate EMAs
            rates_frame['EMA_Median_23'] = rates_frame['Median_Price'].ewm(span=23, adjust=False).mean()
            rates_frame['EMA_Close_10'] = rates_frame['close'].ewm(span=10, adjust=False).mean()
            
            # Generate signals
            rates_frame['Signal'] = 0
            rates_frame.loc[(rates_frame['EMA_Close_10'].shift(1) < rates_frame['EMA_Median_23'].shift(1)) & 
                          (rates_frame['EMA_Close_10'] > rates_frame['EMA_Median_23']), 'Signal'] = 1  # Bullish
            rates_frame.loc[(rates_frame['EMA_Close_10'].shift(1) > rates_frame['EMA_Median_23'].shift(1)) & 
                          (rates_frame['EMA_Close_10'] < rates_frame['EMA_Median_23']), 'Signal'] = -1  # Bearish
            
            # Check for valid signals in the latest candle
            latest_signal = rates_frame['Signal'].iloc[-1]
            
            # Validate trend after crossover
            if latest_signal != 0:
                trend_period = 5
                if latest_signal == 1:  # Bullish signal
                    # Check if we have enough data to validate trend
                    if len(rates_frame) >= trend_period + 1:
                        recent_ema = rates_frame['EMA_Close_10'].iloc[-trend_period:]
                        print("Bullish section")
                        if recent_ema.is_monotonic_increasing:
                            print(f"Valid bullish signal detected at {rates_frame.index[-1]}")
                            # result = place_market_order(symbol, "BUY", lot_size, sl_points, tp_points)
                            # if result and result.retcode == mt.TRADE_RETCODE_DONE:
                            #     print(f"Buy order placed successfully: {result.order}")
                            # else:
                            #     print(f"Order failed: {result.comment if result else 'Unknown error'}")
                
                elif latest_signal == -1:  # Bearish signal
                    if len(rates_frame) >= trend_period + 1:
                        recent_ema = rates_frame['EMA_Close_10'].iloc[-trend_period:]
                        if recent_ema.is_monotonic_decreasing:
                            rates_frame["Trending"] = "Decreasing"
                            print(f"Valid bearish signal detected at {rates_frame.index[-1]}")
                            # result = place_market_order(symbol, "SELL", lot_size, sl_points, tp_points)
                            # if result and result.retcode == mt.TRADE_RETCODE_DONE:
                            #     print(f"Sell order placed successfully: {result.order}")
                            # else:
                            #     print(f"Order failed: {result.comment if result else 'Unknown error'}")
            
            # Position management
            positions = mt.positions_get(symbol=symbol)
            if positions:
                for position in positions:
                    # Check if we should close any positions based on your criteria
                    # Add your position management logic here
                    pass
            
            # display data
            print("\nDisplay dataframe with data")
            print(rates_frame)  
            
            # Wait before next iteration (e.g., 1 minute)
            time.sleep(60 * 5)
            
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        mt.shutdown()
        print("MetaTrader 5 connection closed")

# Example usage
if __name__ == "__main__":
    account_number = os.getenv("ACCOUNT_NUMBER")
    password = os.getenv("PASSWORD")
    start_mt5_bot(5030889311, "PhS!0sIm")