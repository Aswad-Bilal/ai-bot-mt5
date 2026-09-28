"""Market data fetching and MT5 order placement with fallback to demo mode."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

# Try to import MT5, but fallback gracefully if not available
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = False  # Set to True when you connect a real account
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None


def connect_mt5_demo(login: int, password: str, server: str) -> bool:
    """
    Connect to MT5 demo account.
    
    Args:
        login: Your MT5 account number
        password: Your MT5 account password
        server: MT5 server name (e.g., "MetaQuotes-Demo", "XM.COM-Demo")
    
    Returns:
        True if connection successful, False otherwise
    """
    if not MT5_AVAILABLE or mt5 is None:
        print(f"[WARNING] MT5 library not available. Using demo simulator.")
        return False
    
    try:
        if not mt5.initialize(login=login, password=password, server=server):
            print(f"[ERROR] MT5 init failed: {mt5.last_error()}")
            return False
        
        account = mt5.account_info()
        if account is None:
            print(f"[ERROR] Could not get account info: {mt5.last_error()}")
            return False
        
        print(f"✓ Connected to MT5 account: {account.login} on {server}")
        return True
    except Exception as e:
        print(f"[ERROR] MT5 connection error: {e}")
        return False


def fetch_market_data(symbol: str, timeframe: str) -> dict[str, Any]:
    """
    Fetch market data from MT5 or fallback to demo simulator.
    
    Args:
        symbol: Trading pair (e.g., "EURUSD")
        timeframe: Timeframe label (e.g., "5 minutes", "1 hour")
    
    Returns:
        Dictionary with market data including candles, source, and account info
    """
    timeframe_map = {
        "1 minute": mt5.TIMEFRAME_M1 if MT5_AVAILABLE and mt5 else None,
        "5 minutes": mt5.TIMEFRAME_M5 if MT5_AVAILABLE and mt5 else None,
        "15 minutes": mt5.TIMEFRAME_M15 if MT5_AVAILABLE and mt5 else None,
        "30 minutes": mt5.TIMEFRAME_M30 if MT5_AVAILABLE and mt5 else None,
        "1 hour": mt5.TIMEFRAME_H1 if MT5_AVAILABLE and mt5 else None,
        "1 day": mt5.TIMEFRAME_D1 if MT5_AVAILABLE and mt5 else None,
    }
    
    # Try real MT5 connection
    if MT5_AVAILABLE and mt5 and timeframe_map.get(timeframe):
        try:
            candles = mt5.copy_rates_from_pos(symbol, timeframe_map[timeframe], 0, 100)
            if candles is None or len(candles) == 0:
                raise Exception(f"No candles for {symbol}")
            
            account = mt5.account_info()
            return {
                "candles": candles,
                "source": "MetaTrader5 (Live)",
                "account": f"{account.login} ({account.currency})",
                "balance": account.balance,
            }
        except Exception as e:
            print(f"[WARNING] MT5 fetch failed, falling back to demo: {e}")
    
    # Fallback: demo simulator
    return _generate_demo_candles(symbol, timeframe)


def _generate_demo_candles(symbol: str, timeframe: str) -> dict[str, Any]:
    """
    Generate realistic demo candles for testing without a broker.
    
    Args:
        symbol: Trading pair
        timeframe: Timeframe label
    
    Returns:
        Dictionary with simulated OHLCV data
    """
    import numpy as np
    
    # Parse timeframe to minutes
    timeframe_minutes = {
        "1 minute": 1,
        "5 minutes": 5,
        "15 minutes": 15,
        "30 minutes": 30,
        "1 hour": 60,
        "1 day": 1440,
    }.get(timeframe, 5)
    
    # Simulate realistic price data
    num_candles = 100
    base_price = 1.0850 if symbol == "EURUSD" else 1.3000  # Realistic forex prices
    
    # Generate random walk prices
    returns = np.random.normal(0.0001, 0.003, num_candles)
    prices = base_price * np.exp(np.cumsum(returns))
    
    candles = []
    current_time = datetime.utcnow()
    
    for i in range(num_candles - 1, -1, -1):
        time = current_time - timedelta(minutes=timeframe_minutes * (num_candles - i))
        open_price = prices[i]
        close_price = prices[i] * (1 + random.uniform(-0.002, 0.002))
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.001))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.001))
        
        candles.append({
            "time": int(time.timestamp()),
            "open": round(open_price, 5),
            "high": round(high_price, 5),
            "low": round(low_price, 5),
            "close": round(close_price, 5),
            "tick_volume": random.randint(100, 5000),
        })
    
    return {
        "candles": candles,
        "source": "Demo Simulator",
        "account": "Demo Account (USD 10,000)",
        "balance": 10000.0,
    }


def place_demo_trade(symbol: str, direction: str, lot_size: float) -> str:
    """
    Place a trade on MT5 demo account or record it in demo mode.
    
    Args:
        symbol: Trading pair
        direction: "BUY" or "SELL"
        lot_size: Trade volume in lots
    
    Returns:
        Status message
    """
    if not MT5_AVAILABLE or mt5 is None:
        # Demo mode: just log the trade
        return f"[DEMO MODE] {direction} {lot_size} lots of {symbol} order prepared. Check your MT5 terminal or broker account."
    
    try:
        # Get current ask/bid price
        price_info = mt5.symbol_info_tick(symbol)
        if price_info is None:
            raise Exception(f"Cannot get price for {symbol}")
        
        price = price_info.ask if direction == "BUY" else price_info.bid
        
        # Create order request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL,
            "price": price,
            "deviation": 20,
            "comment": "AI Bot Trade",
        }
        
        # Send order
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise Exception(f"Order failed: {result.comment}")
        
        return f"✓ {direction} order placed for {lot_size} lots of {symbol} @ {price}"
    except Exception as e:
        raise Exception(f"Trade placement error: {e}")
