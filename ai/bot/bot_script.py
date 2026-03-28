import requests
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# =============================================
# Telegram Alert for PulseAI
# No browser needed. Instant delivery.
# Works even if WhatsApp Web crashes during demo.
# =============================================

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN")    # from @BotFather
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # from @userinfobot

# =============================================
# Safety check
# =============================================
if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError(
        "TELEGRAM_TOKEN or TELEGRAM_CHAT_ID missing.\n"
        "Follow the setup steps and add them to your .env file."
    )

def send_telegram_alert(ticker, signal_type, score, price, pct_move, anomaly_count, headline=None):
    """
    Sends a Telegram alert when PulseAI detects an anomaly.
    Call this from your main pipeline when anomaly_detected = True.

    Parameters:
        ticker        — stock symbol e.g. "TSLA"
        signal_type   — "positive" or "negative"
        score         — FinBERT sentiment score e.g. -0.91
        price         — price at event e.g. 172.50
        pct_move      — % price move after event e.g. -3.2
        anomaly_count — how many anomalies detected in this session
        headline      — optional: the actual news text that triggered it
    """

    # Emoji and label based on signal direction
    if signal_type == "negative":
        emoji     = "🔴"
        direction = "SELL SIGNAL"
        bar       = "▼" * min(int(abs(score) * 5), 5)
    else:
        emoji     = "🟢"
        direction = "BUY SIGNAL"
        bar       = "▲" * min(int(abs(score) * 5), 5)

    # Triggered by — show headline if available
    trigger_line = ""
    if headline:
        # Truncate long headlines for readability
        short = headline if len(headline) <= 80 else headline[:77] + "..."
        trigger_line = f"\n📰 *Trigger:* {short}\n"

    # Build the full message
    message = (
        f"{emoji} *PulseAI Anomaly Alert*\n"
        f"{'─' * 28}\n"
        f"🏷 Ticker          : `{ticker}`\n"
        f"📊 Signal           : *{direction}*\n"
        f"🧠 Sentiment Score  : `{score:+.2f}` {bar}\n"
        f"💰 Price at Event   : `${price:.2f}`\n"
        f"📉 1h Price Move    : `{pct_move:+.2f}%`\n"
        f"⚡ Anomalies Today  : `{anomaly_count}`\n"
        f"{trigger_line}"
        f"{'─' * 28}\n"
        f"🕐 {datetime.utcnow().strftime('%d %b %Y — %H:%M UTC')}\n"
        f"_PulseAI · Team Order 66 · HackMol 7.0_"
    )

    # Send via Telegram Bot API
    url      = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload  = {
        "chat_id"    : TELEGRAM_CHAT_ID,
        "text"       : message,
        "parse_mode" : "Markdown"   # enables bold, italic, code formatting
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        data     = response.json()

        if data.get("ok"):
            print(f"[SUCCESS] Telegram alert sent for {ticker} — {direction}")
            return True
        else:
            print(f"[ERROR] Telegram API error: {data.get('description')}")
            return False

    except requests.exceptions.Timeout:
        print("[ERROR] Telegram request timed out — check your internet connection.")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False


# =============================================
# Test it standalone — run: python alert_telegram.py
# =============================================
if __name__ == "__main__":
    print("Sending test Telegram alert...\n")
    success = send_telegram_alert(
        ticker        = "TSLA",
        signal_type   = "negative",
        score         = -0.91,
        price         = 172.50,
        pct_move      = -3.20,
        anomaly_count = 2,
        headline      = "Major recall announced for 50,000 Tesla vehicles over software defects"
    )
    if success:
        print("Check your Telegram — message should have arrived instantly.")
    else:
        print("Something went wrong — check your TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in .env")