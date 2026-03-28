import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# warning not crash
if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    print("[Telegram] WARNING: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing — alerts disabled")


def send_telegram_alert(ticker, signal_type, score, price, pct_move, anomaly_count, headline=None):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    if signal_type == "negative":
        emoji     = "🔴"
        direction = "SELL SIGNAL"
        bar       = "▼" * min(int(abs(score) * 5), 5)
    else:
        emoji     = "🟢"
        direction = "BUY SIGNAL"
        bar       = "▲" * min(int(abs(score) * 5), 5)

    trigger_line = ""
    if headline:
        short = headline if len(headline) <= 80 else headline[:77] + "..."
        trigger_line = f"\n📰 *Trigger:* {short}\n"

    message = (
        f"{emoji} *PulseAI Anomaly Alert*\n"
        f"{'─' * 28}\n"
        f"🏷 Ticker          : `{ticker}`\n"
        f"📊 Signal           : *{direction}*\n"
        f"🧠 Sentiment Score  : `{score:+.2f}` {bar}\n"
        f"💰 Price at Event   : `${price:.2f}`\n"
        f"📈 Tomorrow Forecast: `{pct_move:+.2f}%`\n"
        f"⚡ Anomalies Flagged: `{anomaly_count}`\n"
        f"{trigger_line}"
        f"{'─' * 28}\n"
        f"🕐 {datetime.utcnow().strftime('%d %b %Y — %H:%M UTC')}\n"
        f"_PulseAI · Team Order 66 · HackMol 7.0_"
    )

    url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id"   : TELEGRAM_CHAT_ID,
        "text"      : message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        data     = response.json()
        if data.get("ok"):
            print(f"[Telegram] Alert sent for {ticker} — {direction}")
            return True
        else:
            print(f"[Telegram] API error: {data.get('description')}")
            return False
    except requests.exceptions.Timeout:
        print("[Telegram] Request timed out")
        return False
    except Exception as e:
        print(f"[Telegram] Error: {e}")
        return False


if __name__ == "__main__":
    # real test with your actual keys
    from data.fetcher import get_live_price
    live = get_live_price("TSLA")
    
    success = send_telegram_alert(
        ticker        = "TSLA",
        signal_type   = "positive",
        score         = 0.87,
        price         = live.get("price", 0),
        pct_move      = live.get("change_pct", 0),
        anomaly_count = 3,
        headline      = "Tesla smashes Q1 delivery record beating all analyst expectations"
    )
    if success:
        print("Check Telegram — real alert sent.")
    else:
        print("Failed — check .env keys")