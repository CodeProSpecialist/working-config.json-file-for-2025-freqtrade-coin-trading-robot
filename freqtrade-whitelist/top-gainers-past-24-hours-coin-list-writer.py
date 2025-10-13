import ccxt
import datetime
import json
import time
import pytz

# ------------------ Configuration ------------------
API_KEY = 'YOUR_KRAKEN_API_KEY'
API_SECRET = 'YOUR_KRAKEN_SECRET_KEY'

MIN_24H_CHANGE = 0.01    # +1% in 24 hours
MIN_PRICE = 0.10         # Price >= $0.10 per coin
MIN_VOLUME = 1000        # Minimum 24h volume
TOP_N = 70               # Number of pairs to keep
REFRESH_INTERVAL = 24 * 60 * 60  # 24 hours

# ----------------------------------------------------
kraken = ccxt.kraken({
    'apiKey': API_KEY,
    'secret': API_SECRET,
})
kraken.load_markets()

def fetch_ohlcv(symbol, timeframe='1h', since=None, limit=24):
    """Fetch OHLCV safely with logging."""
    try:
        print(f"📊 Fetching {timeframe} OHLCV for {symbol}...")
        return kraken.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
    except Exception as e:
        print(f"⚠️ Error fetching data for {symbol}: {e}")
        return []

def fetch_current_price(symbol):
    """Fetch the current price for a symbol."""
    try:
        ticker = kraken.fetch_ticker(symbol)
        return ticker['last']
    except Exception as e:
        print(f"⚠️ Error fetching current price for {symbol}: {e}")
        return None

def calc_24h_change(symbol, start_time):
    """Calculate 24-hour % price change and total volume."""
    ohlcv = fetch_ohlcv(symbol, timeframe='1h', since=int(start_time.timestamp() * 1000))
    current_price = fetch_current_price(symbol)
    if not ohlcv or current_price is None:
        print(f"⚠️ Not enough data or no current price for {symbol}")
        return 0, 0, 0
    start_price = ohlcv[0][1]  # Opening price of first candle
    volume = sum(x[5] for x in ohlcv)  # Total volume over 24 hours
    price_change = (current_price - start_price) / start_price
    return price_change, volume, current_price

def generate_whitelist():
    print("\n🚀 Starting whitelist generation process...")
    kraken_pairs = [s for s in kraken.symbols if s.endswith('/USD')]
    print(f"Found {len(kraken_pairs)} USD pairs on Kraken.")

    valid_pairs = []
    one_day_ago = datetime.datetime.now(pytz.utc) - datetime.timedelta(days=1)

    for i, pair in enumerate(kraken_pairs, start=1):
        print(f"\n[{i}/{len(kraken_pairs)}] Checking {pair}...")

        # 24-hour change
        change_24h, volume_24h, current_price = calc_24h_change(pair, one_day_ago)
        print(f"  24H change: {change_24h:.2%}, Volume: {volume_24h:.0f}, Current Price: ${current_price:.2f}")

        # Check volume
        if volume_24h < MIN_VOLUME:
            print("  ❌ Rejected: not enough volume.")
            continue

        # Check 24-hour change
        if change_24h < MIN_24H_CHANGE:
            print("  ❌ Rejected: not enough 24-hour growth.")
            continue

        # Check price
        if current_price is None or current_price < MIN_PRICE:
            print(f"  ❌ Rejected: current price (${current_price if current_price else 'N/A'}) below ${MIN_PRICE}.")
            continue

        print("  ✅ Accepted.")
        valid_pairs.append((pair, change_24h))
        time.sleep(1)  # Avoid hitting API rate limit

    # Sort by 24-hour change (highest to lowest)
    valid_pairs.sort(key=lambda x: x[1], reverse=True)
    final_pairs = [(p[0], p[1]) for p in valid_pairs[:TOP_N]]  # Keep pair and change for output

    print(f"\n💾 Saving top {len(final_pairs)} pairs to whitelist.json...")
    with open('whitelist.json', 'w') as f:
        json.dump([p[0] for p in final_pairs], f, indent=2)  # Only pairs in JSON

    print("\n✅ Whitelist updated successfully (sorted by highest 24h price increase):")
    for pair, change in final_pairs:
        print(f"   - {pair}: +{change:.2%}")

def main():
    while True:
        start_time = datetime.datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"\n==============================")
        print(f"🕒 New Run: {start_time}")
        print(f"==============================")

        generate_whitelist()

        print(f"\n⏸ Sleeping for {REFRESH_INTERVAL/3600:.1f} hours (≈24h)...")
        for remaining in range(REFRESH_INTERVAL, 0, -3600):
            hours_left = remaining // 3600
            print(f"   ...{hours_left} hours remaining...")
            time.sleep(3600)
        print("\n🔁 Waking up to refresh whitelist...\n")

if __name__ == "__main__":
    main()
