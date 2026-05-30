import time
import requests
from datetime import datetime

# ============================
TELEGRAM_BOT_TOKEN = "8662805862:AAELqLSHd9iROH2ONQ_eQ6rN1-A_ppXbhBM"
TELEGRAM_CHANNEL_ID = "@pxpriceq"
INTERVAL_SECONDS = 30
ALERT_THRESHOLD = 5.0
# ============================

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

prev_prices  = {"PX": None, "BTC": None, "ETH": None, "Gold": None, "Silver": None, "USDT": None, "USD": None}
base_prices  = {"PX": None, "BTC": None, "ETH": None, "Gold": None, "Silver": None, "USDT": None, "USD": None}


def fetch_mexc(symbol):
    try:
        r = requests.get(f"https://api.mexc.com/api/v3/ticker/price?symbol={symbol}", timeout=10, headers=HEADERS)
        return float(r.json()["price"]) if r.status_code == 200 else None
    except: return None

def fetch_binance(symbol):
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=10, headers=HEADERS)
        return float(r.json()["price"]) if r.status_code == 200 else None
    except: return None

def fetch_silver():
    try:
        r = requests.get("https://api.coinbase.com/v2/prices/XAG-USD/spot", timeout=10, headers=HEADERS)
        return float(r.json()["data"]["amount"]) if r.status_code == 200 else None
    except: return None

def fetch_bitpin_usdt():
    try:
        r = requests.get("https://api.bitpin.org/v1/mkt/markets/", timeout=10, headers=HEADERS)
        if r.status_code == 200:
            for item in r.json().get("results", []):
                if item.get("code") == "USDT_IRT":
                    return float(item.get("price", 0)) / 10
        return None
    except: return None

def fetch_dollar_tgju():
    try:
        r = requests.get("https://api.tgju.org/v1/market/indicator/summary-table-data/price_dollar_rl", timeout=10, headers=HEADERS)
        if r.status_code == 200:
            return float(r.json()["data"][0][1].replace(",", "")) / 10
        return None
    except: return None

def fetch_all_prices():
    return {
        "PX":     fetch_mexc("PXUSDT"),
        "BTC":    fetch_binance("BTCUSDT"),
        "ETH":    fetch_binance("ETHUSDT"),
        "Gold":   fetch_binance("PAXGUSDT"),
        "Silver": fetch_silver(),
        "USDT":   fetch_bitpin_usdt(),
        "USD":    fetch_dollar_tgju(),
    }


def fmt_price(price, toman=False):
    if price is None: return "—"
    if toman: return f"{price:,.0f}"
    if price < 0.01:  return f"{price:.6f}"
    elif price < 1:   return f"{price:.4f}"
    elif price < 100: return f"{price:.2f}"
    else:             return f"{price:,.2f}"

def fmt_change(cur, prev):
    if cur is None or prev is None: return ("", "")
    pct = ((cur - prev) / prev) * 100
    if pct > 0:   return ("🟢", f"+{pct:.2f}%")
    elif pct < 0: return ("🔴", f"{pct:.2f}%")
    else:         return ("⚪️", "0.00%")

def format_main_message(prices):
    now  = datetime.now().strftime("%H:%M:%S")
    date = datetime.now().strftime("%Y/%m/%d")

    def row(emoji, name, unit="$", toman=False):
        p = prices.get(name)
        dot, chg = fmt_change(p, prev_prices.get(name))
        price_str = fmt_price(p, toman)
        suffix = " ت" if toman else ""
        if p is None:
            return f"│ {emoji} <b>{name:<6}</b>  —\n"
        return f"│ {emoji} <b>{name:<6}</b>  {unit}{price_str}{suffix}  {dot} <code>{chg}</code>\n"

    msg  = f"╔═══ 📊 <b>قیمت لحظه‌ای</b> ═══╗\n"
    msg += f"║  🗓 {date}   🕐 {now}\n"
    msg += f"╠═══════════════════════╣\n"
    msg += row("🔵", "PX")
    msg += row("🟡", "BTC")
    msg += row("🔷", "ETH")
    msg += f"│ ─────────────────── │\n"
    msg += row("🥇", "Gold")
    msg += row("🥈", "Silver")
    msg += f"│ ─────────────────── │\n"
    msg += row("💵", "USD", unit="", toman=True)
    msg += row("💚", "USDT", unit="", toman=True)
    msg += f"╚═══════════════════════╝\n"
    msg += f"<i>🏦 MEXC · Binance · Coinbase · TGJU</i>"
    return msg


def check_alerts(prices):
    alerts = []
    for name, price in prices.items():
        if price is None or base_prices[name] is None: continue
        pct = ((price - base_prices[name]) / base_prices[name]) * 100
        if abs(pct) >= ALERT_THRESHOLD:
            arrow = "🚀" if pct > 0 else "🔻"
            alerts.append(f"{arrow} <b>{name}</b>  {pct:+.2f}%")
    return alerts


def send_message(text):
    try:
        resp = requests.post(TELEGRAM_API_URL, json={
            "chat_id": TELEGRAM_CHANNEL_ID,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=10)
        return resp.status_code == 200
    except: return False


def main():
    global prev_prices, base_prices
    print("✅ ربات شروع به کار کرد...")

    while True:
        prices = fetch_all_prices()

        ok = send_message(format_main_message(prices))
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] {'✅' if ok else '❌'} | BTC={prices.get('BTC')} Silver={prices.get('Silver')} USD={prices.get('USD')}")

        alerts = check_alerts(prices)
        if alerts:
            alert_msg = (
                "╔══ ⚠️ <b>هشدار نوسان!</b> ══╗\n"
                + "\n".join(alerts) +
                "\n╚═══════════════════╝"
            )
            send_message(alert_msg)
            print(f"[{now}] 🚨 اخطار نوسان ارسال شد")
            for name, price in prices.items():
                if price and base_prices[name] and abs(((price - base_prices[name]) / base_prices[name]) * 100) >= ALERT_THRESHOLD:
                    base_prices[name] = price

        for name, price in prices.items():
            if price:
                prev_prices[name] = price
                if base_prices[name] is None:
                    base_prices[name] = price

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
