# PulseAI 📡
### Autonomous Financial Market Intelligence for Retail Investors

> *By the time you read the news, the market has already moved.*  
> *Big funds have armies of analysts watching 24/7. Everyone else is flying blind.*  
> *PulseAI is the equaliser.*

**Team Order 66 — HackMol 7.0**  
Thapar Institute of Engineering & Technology, Patiala

| Member | Role |
|---|---|
| Simarbir Singh Sandhu | AI Pipeline — FinBERT, Anomaly Detection, LLM, Agent |
| Sanveer Singh | Data Pipeline, Backend (FastAPI), Backtester |
| Jaspreet Singh | Data Fetcher, Multi-source Aggregation |
| Harshjot Singh | Frontend (Streamlit), Dashboard UI |

---

## What is PulseAI?

PulseAI is an autonomous financial intelligence agent that watches stocks 24/7, detects sentiment anomalies the moment they emerge, cross-references with a price prediction model, and delivers plain-English alerts to your Telegram — with zero human trigger.

You set a target. The agent handles everything else.

**How it's different from ChatGPT:**  
ChatGPT tells you what happened. PulseAI tells you what's statistically significant *right now*. FinBERT scored 47 data points from 7 sources. Z-score detected anomalies at 1.9 standard deviations. Prophet predicted price movement direction. Both signals aligned — STRONG BUY, high confidence. That's not a chatbot. That's an intelligence system.

---

## Features

- **Autonomous Agent Loop** — watches stocks 24/7, no human trigger required
- **FinBERT Sentiment Engine** — finance-specific BERT model that understands market language, not just positive/negative
- **Two-Layer Anomaly Detection** — Z-score catches sudden spikes, Isolation Forest catches structural outliers
- **Prophet Price Prediction** — 2 years of historical data, next-day price forecast with confidence intervals
- **Combined Signal** — STRONG BUY / WEAK BUY / HOLD / WEAK SELL / STRONG SELL based on sentiment + price model alignment
- **Multi-Source Intelligence** — 7 data sources unified into one signal
- **Auto Brief Generation** — Llama 3 writes a plain-English brief the moment a signal fires
- **Telegram Alerts** — push notification to your phone when anomaly detected
- **Live Dashboard** — candlestick charts, sentiment scores, flagged headlines, AI brief
- **Market Context** — VIX fear index, S&P 500 momentum, Put/Call ratio
- **Signal Validation** — 100% accuracy on 3 known historical market events

---

## Tech Stack

| Layer | Technology |
|---|---|
| Sentiment | FinBERT via HuggingFace Inference API (`ProsusAI/finbert`) |
| Anomaly Detection | Z-score + Isolation Forest (scikit-learn) |
| Price Prediction | Prophet (Meta's time series model) |
| Agent Orchestration | Python async + LangGraph-style loop |
| LLM | Groq API — Llama 3.1 8B Instant |
| Data — News | NewsAPI + Yahoo Finance RSS + Finnhub |
| Data — Social | StockTwits (Reddit replacement, no API key needed) |
| Data — Fundamentals | yfinance (price, analyst ratings, earnings) |
| Data — Insider | SEC EDGAR Form 4 filings (free government API) |
| Data — Trends | Google Trends via pytrends |
| Backend | FastAPI + Uvicorn |
| Frontend | Streamlit + Plotly |
| Notifications | Telegram Bot API |
| Environment | python-dotenv |

---

## Repo Structure

```
pulseai-hackmol/
│
├── ai/                          # AI domain — Simarbir's work
│   ├── sentiment/
│   │   └── finbert.py           # FinBERT scoring via HuggingFace API
│   ├── anomaly/
│   │   └── detector.py          # Z-score + Isolation Forest detection
│   ├── llm/
│   │   └── groq_client.py       # Groq/Llama 3 brief generation
│   ├── agent/
│   │   └── loop.py              # Autonomous agent loop (run_loop + run_once)
│   ├── prediction/
│   │   └── prophet_model.py     # Prophet price forecasting
│   ├── notifications/
│   │   ├── __init__.py
│   │   └── telegram_bot.py      # Telegram alert sender
│   └── pipeline.py              # Clean entry point — start_background_loop()
│
├── backend/                     # FastAPI backend — Sanveer's work
│   ├── main.py                  # App init, startup, push_signal callback
│   ├── routes/
│   │   └── signals.py           # All API endpoints
│   ├── services/
│   │   └── ai_service.py        # Bridge between backend and AI
│   └── backtester.py            # Historical signal validation
│
├── data/                        # Data pipeline — Jaspreet's work
│   ├── __init__.py
│   └── fetcher.py               # Multi-source async fetcher (7 sources)
│
├── frontend/                    # Streamlit dashboard — Harshjot's work
│   ├── app.py                   # Main dashboard
│   └── loader.py                # API client + data mapping
│
├── .env.example                 # Environment variable template
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Data Flow

```
NewsAPI → ┐
Yahoo RSS → ┤
StockTwits → ┤→ Data Aggregator → FinBERT Scoring → Anomaly Detection
yfinance → ┤         (fetcher.py)    (finbert.py)      (detector.py)
SEC EDGAR → ┤                                               ↓
Finnhub → ┘                                         Signal Detected?
                                                     YES ↓        NO ↓
                                              Prophet Forecast   Continue
                                                     ↓            Loop
                                              Groq LLM Brief
                                                     ↓
                                         FastAPI Backend Cache
                                                     ↓
                                    Streamlit Dashboard + Telegram Alert
```

---

## Anomaly Detection — How It Works

**Layer 1 — Z-score (stateless, fast):**
Every headline gets a FinBERT sentiment score (-1 to +1). Z-score measures how many standard deviations a score is from the batch mean. Anything beyond ±1.5 gets flagged immediately.

```
avg sentiment = 0.24
std deviation = 0.45
Gary Black warning score = -0.87
z = (-0.87 - 0.24) / 0.45 = -2.46  ← flagged
```

**Layer 2 — Isolation Forest (structural):**
Plots all scores as points. Measures how many random cuts it takes to isolate each point. Outliers sitting alone in sparse regions get isolated in very few cuts — flagged. Clustered points require many cuts — not flagged.

**Why both?** Z-score misses coordinated negative sentiment clusters (all scores are low but none are extreme individually). Isolation Forest misses sudden single spikes in volatile data. Together they cover each other's blind spots.

---

## Combined Signal Logic

```
Sentiment bullish + Price model bullish  →  STRONG BUY   (confidence: high)
Sentiment bullish OR Price model bullish →  WEAK BUY     (confidence: medium)
Neither bullish                          →  HOLD          (confidence: low)
Sentiment bearish OR Price bearish       →  WEAK SELL    (confidence: medium)
Sentiment bearish + Price bearish        →  STRONG SELL  (confidence: high)
```

VIX above 30 (extreme fear) automatically downgrades confidence by one level — a STRONG BUY becomes WEAK BUY in a fear market.

---

## Signal Validation (Backtest)

We validated PulseAI on three known historical market events:

| Event | Ticker | Date | Expected | Our Signal | Outcome |
|---|---|---|---|---|---|
| Adani-Hindenburg Report | ADANIENT.NS | 2023-01-24 | Negative spike | Negative spike | ✅ TP |
| Tesla Q4 2022 Earnings Miss | TSLA | 2023-01-25 | Negative spike | Negative spike | ✅ TP |
| Tesla Cybertruck Recall | TSLA | 2024-02-15 | Negative spike | Negative spike | ✅ TP |

**Accuracy: 100% | Precision: 100% | Recall: 100%**

> Note: This is signal validation on known events, not a full quantitative backtest. A production backtest would require a paid historical news API across hundreds of events. This proves the detection logic is sound — full backtesting is on the roadmap.

---

## Setup

### Prerequisites
- Python 3.10+
- Conda or virtualenv recommended

### 1. Clone the repo
```bash
git clone https://github.com/Simarbir2112006/pulseai-hackmol.git
cd pulseai-hackmol
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:
```
HF_TOKEN=             # HuggingFace token — huggingface.co/settings/tokens
GROQ_API_KEY=         # Groq API key — console.groq.com
NEWS_API_KEY=         # NewsAPI key — newsapi.org
FINNHUB_KEY=          # Finnhub key — finnhub.io (optional)
TELEGRAM_BOT_TOKEN=   # From @BotFather on Telegram
TELEGRAM_CHAT_ID=     # From @userinfobot on Telegram
POLL_INTERVAL=60      # Agent polling interval in seconds
```

### 4. Run the backend
```bash
python -m uvicorn backend.main:app --reload
```

Backend runs at `http://localhost:8000`  
API docs at `http://localhost:8000/docs`

### 5. Run the frontend
```bash
cd frontend
streamlit run app.py
```

Dashboard runs at `http://localhost:8501`

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/signals/latest?ticker=TSLA` | Latest signal with sentiment, anomaly, prediction, brief |
| GET | `/signals/history?ticker=TSLA` | All signals since startup |
| GET | `/signals/prediction?ticker=TSLA` | Prophet price forecast only |
| GET | `/signals/price?ticker=TSLA` | Live current price from yfinance |
| GET | `/signals/market` | VIX, S&P 500 momentum, Put/Call ratio |
| GET | `/signals/watchlist` | Current watchlist |
| POST | `/signals/watchlist/add?ticker=AAPL` | Add ticker to watchlist |
| POST | `/signals/watchlist/remove?ticker=AAPL` | Remove ticker |
| GET | `/signals/backtest?event=adani` | Run historical signal validation |
| GET | `/signals/health` | Server health check |

### Sample Response — `/signals/latest?ticker=TSLA`
```json
{
  "ticker": "TSLA",
  "timestamp": "2026-03-28T18:00:00",
  "detected": true,
  "signal_type": "positive_spike",
  "avg_sentiment": 0.312,
  "item_count": 47,
  "flagged_items": [
    {
      "text": "Tesla smashes Q1 delivery record beating analyst expectations",
      "score": 0.94,
      "source": "newsapi",
      "timestamp": "2026-03-28T13:00:00Z",
      "z_score": 1.92
    }
  ],
  "prediction": {
    "current_price": 361.83,
    "predicted_tomorrow": 377.15,
    "predicted_tomorrow_date": "2026-03-29",
    "pct_change_tomorrow": 4.23,
    "direction": "up",
    "confidence_interval_tomorrow": {
      "lower": 342.95,
      "upper": 410.62
    }
  },
  "combined_signal": {
    "verdict": "STRONG BUY",
    "confidence": "high",
    "sentiment_aligned": true,
    "price_aligned": true
  },
  "brief": {
    "summary": "Tesla's stock is showing strong bullish momentum driven by record deliveries and AI chip expansion plans.",
    "why_it_matters": "Multiple sources confirm positive sentiment across news and analyst ratings, with price model predicting continued upward movement.",
    "what_this_means": "If you follow Tesla, this may be worth watching closely. Strong fundamentals and aligned signals suggest continued positive momentum.",
    "confidence": "High",
    "signal": "BUY",
    "sources_used": ["newsapi", "yahoo_rss", "yf_analyst", "sec_edgar"]
  }
}
```

---

## Running the Backtester

```bash
# Run all events
python backend/backtester.py

# Run single event
python backend/backtester.py --event adani
python backend/backtester.py --event tsla_earnings
python backend/backtester.py --event cybertruck

# Filter by ticker
python backend/backtester.py --ticker TSLA
```

Or via the dashboard — click **"Model Validation — Historical Backtest"** and hit **Run Backtest Now**.

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `HF_TOKEN` | Yes | HuggingFace API token for FinBERT inference |
| `GROQ_API_KEY` | Yes | Groq API key for Llama 3 brief generation |
| `NEWS_API_KEY` | Yes | NewsAPI key for financial headlines |
| `FINNHUB_KEY` | No | Finnhub key for analyst ratings and earnings data |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot token for push alerts |
| `TELEGRAM_CHAT_ID` | No | Your Telegram chat ID for receiving alerts |
| `POLL_INTERVAL` | No | Agent polling interval in seconds (default: 60) |

> StockTwits, Yahoo Finance RSS, SEC EDGAR, and yfinance require no API keys.

---

## How to Get API Keys

**HuggingFace Token:**
1. Go to [huggingface.co](https://huggingface.co) → Settings → Access Tokens
2. Create a new token with read permissions

**Groq API Key:**
1. Go to [console.groq.com](https://console.groq.com)
2. Create account → API Keys → Create new key

**NewsAPI Key:**
1. Go to [newsapi.org](https://newsapi.org)
2. Register → get your API key from the dashboard

**Finnhub Key:**
1. Go to [finnhub.io](https://finnhub.io)
2. Register → API Keys → copy free key

**Telegram Bot:**
1. Open Telegram → search `@BotFather`
2. Send `/newbot` → follow prompts → copy the token
3. Start a chat with your bot → send any message
4. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates` → copy `chat.id`

---

## Target Audience

- **Retail investors** — individuals managing personal portfolios
- **Equity analysts** — who manually track dozens of fragmented sources today
- **SME fund managers** — who need institutional-grade intelligence without institutional budgets

**Market size:** $11 billion retail fintech market — targeting the underserved retail and SME segment that existing platforms priced at lakhs/year ignore completely.

---

## Future Roadmap

- **Multi-asset tracking** — crypto, commodities, forex
- **Full quantitative backtest** — hundreds of events with paid historical news API
- **Reddit + Twitter integration** — when API access is approved
- **Personalised portfolio watchlists** — unlimited tickers, priority ranking
- **Predictive scoring** — rank signals by historical reliability per ticker
- **Mobile app** — iOS and Android push notifications
- **WhatsApp alerts** — via Twilio integration
- **API product** — for quant funds and algo trading systems to plug into directly
- **Intraday sentiment** — higher frequency polling for day traders

---

## Known Limitations

- NewsAPI free tier returns articles up to 24 hours old — real-time requires paid tier
- Prophet is a daily model — next-day forecast only, not intraday
- FinBERT via HuggingFace Inference API has cold start latency (~20s) on first request
- StockTwits API rate limits at ~200 requests/hour
- Signal validation uses 3 events — full backtesting requires paid historical data API
- Duplicate items may appear in flagged_items when Z-score and Isolation Forest both flag the same headline

---

## License

MIT License — built for HackMol 7.0 by Team Order 66.