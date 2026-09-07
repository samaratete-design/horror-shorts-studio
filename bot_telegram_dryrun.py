import time
import logging
import yfinance as yf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
)
logger = logging.getLogger("DryRunBot")

# --- إعدادات عامة ---
SYMBOLS = ["BTC-USD", "GC=F"]

FAST_PERIOD = 5
SLOW_PERIOD = 20
ATR_PERIOD = 14
ATR_MULTIPLIER = 1.0

INTERVAL = "1m"
FETCH_LIMIT = 50

RISK_PERCENT = 0.02
RR_RATIO = 2.0
STARTING_BALANCE = 10.0

state = {
    symbol: {"position": None, "last_signal": None}
    for symbol in SYMBOLS
}


def fetch_candles(symbol: str, interval: str, limit: int) -> list[dict]:
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d", interval=interval)
        data = data.dropna(subset=["High", "Low", "Close"])
        candles = [
            {"high": h, "low": l, "close": c}
            for h, l, c in zip(data["High"], data["Low"], data["Close"])
        ]
        return candles[-limit:]
    except Exception as e:
        logger.error(f"[{symbol}] Error fetching data: {e}")
        return []


def calculate_sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def calculate_atr(candles, period):
    if len(candles) < period:
        return None
    true_ranges = [c["high"] - c["low"] for c in candles[-period:]]
    return sum(true_ranges) / period


def open_position(symbol, direction, entry_price, balance):
    risk_amount = balance * RISK_PERCENT
    sl_distance = entry_price * 0.01
    size = risk_amount / sl_distance

    if direction == "BUY":
        sl = entry_price - sl_distance
        tp = entry_price + (sl_distance * RR_RATIO)
    else:
        sl = entry_price + sl_distance
        tp = entry_price - (sl_distance * RR_RATIO)

    position = {"direction": direction, "entry_price": entry_price, "size": size, "sl": sl, "tp": tp}

    logger.info(
        f"[{symbol}] >>> OPEN {direction} | Entry={entry_price:.5f} Size={size:.4f} "
        f"SL={sl:.5f} TP={tp:.5f} Risk={risk_amount:.2f}"
    )
    return position


def close_position(symbol, position, exit_price, balance, reason):
    if position["direction"] == "BUY":
        pnl = (exit_price - position["entry_price"]) * position["size"]
    else:
        pnl = (position["entry_price"] - exit_price) * position["size"]

    new_balance = balance + pnl
    logger.info(
        f"[{symbol}] <<< CLOSE ({reason}) | Exit={exit_price:.5f} PnL={pnl:.2f} "
        f"NewBalance={new_balance:.2f}"
    )
    return new_balance


def check_sl_tp(position, current_price):
    if position["direction"] == "BUY":
        if current_price <= position["sl"]:
            return "SL"
        if current_price >= position["tp"]:
            return "TP"
    else:
        if current_price >= position["sl"]:
            return "SL"
        if current_price <= position["tp"]:
            return "TP"
    return None


def process_symbol(symbol, balance):
    sym_state = state[symbol]

    candles = fetch_candles(symbol, INTERVAL, FETCH_LIMIT)
    min_needed = SLOW_PERIOD + ATR_PERIOD + 1

    if len(candles) < min_needed:
        logger.info(f"[{symbol}] بيانات غير كافية ({len(candles)}/{min_needed})")
        return balance

    closed_candles = candles[:-1]
    closes = [c["close"] for c in closed_candles]
    current_price = candles[-1]["close"]

    fast_sma = calculate_sma(closes, FAST_PERIOD)
    slow_sma = calculate_sma(closes, SLOW_PERIOD)
    atr = calculate_atr(closed_candles, ATR_PERIOD)

    if fast_sma is None or slow_sma is None or atr is None:
        return balance

    position = sym_state["position"]

    logger.info(
        f"[{symbol}] Price={current_price:.5f} FastSMA={fast_sma:.5f} "
        f"SlowSMA={slow_sma:.5f} ATR={atr:.5f} Balance={balance:.2f} "
        f"Position={position['direction'] if position else 'None'}"
    )

    if position is not None:
        hit = check_sl_tp(position, current_price)
        if hit:
            balance = close_position(symbol, position, current_price, balance, hit)
            position = None
            sym_state["position"] = None

    new_signal = None
    if fast_sma > slow_sma:
        new_signal = "BUY"
    elif fast_sma < slow_sma:
        new_signal = "SELL"

    if new_signal is None or new_signal == sym_state["last_signal"]:
        return balance

    gap_abs = abs(fast_sma - slow_sma)
    if gap_abs < ATR_MULTIPLIER * atr:
        logger.info(
            f"[{symbol}] Signal REJECTED (gap={gap_abs:.5f} < "
            f"threshold={ATR_MULTIPLIER * atr:.5f})"
        )
        return balance

    if position is not None and position["direction"] != new_signal:
        balance = close_position(symbol, position, current_price, balance, "REVERSE")
        position = None
        sym_state["position"] = None

    if position is None:
        sym_state["position"] = open_position(symbol, new_signal, current_price, balance)
        sym_state["last_signal"] = new_signal

    return balance


def main():
    logger.info("Starting DRY-RUN bot (no Telegram, no real orders)...")
    logger.info(f"Symbols: {SYMBOLS} | Filter: Confirmed-Close + ATR({ATR_PERIOD}) x{ATR_MULTIPLIER}")

    balance = STARTING_BALANCE

    while True:
        try:
            for symbol in SYMBOLS:
                balance = process_symbol(symbol, balance)
            time.sleep(30)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(10)


if __name__ == "__main__":
    main()
