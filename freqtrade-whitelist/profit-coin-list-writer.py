import ccxt
import datetime
import json
import time
import pytz

# ------------------ Configuration ------------------
API_KEY = 'YOUR_KRAKEN_API_KEY'
API_SECRET = 'YOUR_KRAKEN_SECRET_KEY'

MIN_2M_CHANGE = 0.10     # +10% in 2 months
MIN_4D_CHANGE = 0.05     # +5% in 4 days
MIN_24H_CHANGE = 0.01    # +1% in 24 hours
MIN_PRICE = 10.0         # Price > $10 per coin
MIN_VOLUME = 1000
TOP_N = 70              # how many pairs to keep
REFRESH_INTERVAL = 24 * 60 * 60  # 24 hours

# ----------------------------------------------------
kraken = ccxt.kraken({
    'apiKey': API_KEY,
    'secret': API_SECRET,
})
kraken.load_markets()

utc_now = datetime.datetime.now(pytz.utc)
two_months_ago = utc_now - datetime.timedelta(days=60)
four_days_ago = utc_now - datetime.timedelta(days=4)
one_day_ago = utc_now - datetime.timedelta(days=1)

def fetch_ohlcv(symbol, timeframe='1d', since=None, limit=100):
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

def calc_change(symbol, start_time, timeframe='1d'):
    """Calculate % price change and total volume since given time."""
    if timeframe == '1h':  # For 24-hour change, use current price
        ohlcv = fetch_ohlcv(symbol, timeframe, since=int(start_time.timestamp() * 1000), limit=24)
        current_price = fetch_current_price(symbol)
        if not ohlcv or current_price is None:
            print(f"⚠️ Not enough data or no current price for {symbol}")
            return 0, 0
        start_price = ohlcv[0][1]  # Opening price of first candle
        volume = sum(x[5] for x in ohlcv)
        price_change = (current_price - start_price) / start_price
        return price_change, volume, current_price
    else:
        ohlcv = fetch_ohlcv(symbol, timeframe, since=int(start_time.timestamp() * 1000))
        if len(ohlcv) < 2:
            print(f"⚠️ Not enough data for {symbol}")
            return 0, 0, 0
        start_price = ohlcv[0][1]
        end_price = ohlcv[-1][4]
        volume = sum(x[5] for x in ohlcv)
        price_change = (end_price - start_price) / start_price
        return price_change, volume, end_price

def generate_whitelist():
    print("\n🚀 Starting whitelist generation process...")
    kraken_pairs = [s for s in kraken.symbols if s.endswith('/USD')]
    print(f"Found {len(kraken_pairs)} USD pairs on Kraken.")

    valid_pairs = []

    for i, pair in enumerate(kraken_pairs, start=1):
        print(f"\n[{i}/{len(kraken_pairs)}] Checking {pair}...")

        # 2-month change (use 1d timeframe)
        change_2m, vol_2m, price_2m = calc_change(pair, two_months_ago, timeframe='1d')
        print(f"  2M change: {change_2m:.2%}, Volume: {vol_2m:.0f}")
        if vol_2m < MIN_VOLUME or change_2m < MIN_2M_CHANGE:
            print("  ❌ Rejected: not enough long-term growth or volume.")
            continue

        # 4-day change (use 1d timeframe)
        change_4d, _, price_4d = calc_change(pair, four_days_ago, timeframe='1d')
        print(f"  4D change: {change_4d:.2%}")
        if change_4d < MIN_4D_CHANGE:
            print("  ❌ Rejected: not enough short-term growth.")
            continue

        # 24-hour change (use 1h timeframe and current price)
        change_24h, _, current_price = calc_change(pair, one_day_ago, timeframe='1h')
        print(f"  24H change: {change_24h:.2%}, Current Price: ${current_price:.2f}")
        if change_24h < MIN_24H_CHANGE:
            print("  ❌ Rejected: not enough short-term growth.")
            continue

        # Check if current price is greater than $75
        if current_price is None or current_price < MIN_PRICE:
            print(f"  ❌ Rejected: current price (${current_price if current_price else 'N/A'}) below ${MIN_PRICE}.")
            continue

        print("  ✅ Accepted.")
        valid_pairs.append((pair, vol_2m))
        time.sleep(1)  # avoid hitting API rate limit

    # Sort and trim
    valid_pairs.sort(key=lambda x: x[1], reverse=True)
    final_pairs = [p[0] for p in valid_pairs[:TOP_N]]

    print(f"\n💾 Saving top {len(final_pairs)} pairs to whitelist.json...")
    with open('whitelist.json', 'w') as f:
        json.dump(final_pairs, f, indent=2)

    print("\n✅ Whitelist updated successfully:")
    for p in final_pairs:
        print("   -", p)

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
