from prophet import Prophet
import yfinance as yf
import pandas as pd
from datetime import datetime


def fetch_price_history(ticker: str) -> pd.DataFrame:
    stock = yf.Ticker(ticker)
    hist = stock.history(period="2y")  # 2 years gives Prophet enough pattern
    df = hist[["Close"]].reset_index()
    df.columns = ["ds", "y"]
    df["ds"] = df["ds"].dt.tz_localize(None)
    return df


def predict(ticker: str, days_ahead: int = 7) -> dict:
    try:
        df = fetch_price_history(ticker)

        if len(df) < 60:
            return {"error": "Not enough price history"}

        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=True,
            changepoint_prior_scale=0.01,  # much lower — less reactive to recent swings
            seasonality_prior_scale=5,
            interval_width=0.80
        )
        model.fit(df)

        future = model.make_future_dataframe(periods=days_ahead, freq="B")  # B = business days only
        forecast = model.predict(future)

        last_actual = df["y"].iloc[-1]
        last_date = df["ds"].iloc[-1]

        tomorrow_row = forecast[forecast["ds"] > last_date].iloc[0]
        week_row = forecast[forecast["ds"] > last_date].iloc[-1]

        predicted_tomorrow = tomorrow_row["yhat"]
        predicted_week = week_row["yhat"]

        pct_tomorrow = round(((predicted_tomorrow - last_actual) / last_actual) * 100, 2)
        pct_week = round(((predicted_week - last_actual) / last_actual) * 100, 2)

        return {
            "ticker": ticker,
            "timestamp": datetime.utcnow().isoformat(),
            "current_price": round(last_actual, 2),
            "last_date": str(last_date.date()),
            "predicted_tomorrow": round(predicted_tomorrow, 2),
            "predicted_tomorrow_date": str(tomorrow_row["ds"].date()),
            "predicted_week": round(predicted_week, 2),
            "predicted_week_date": str(week_row["ds"].date()),
            "pct_change_tomorrow": pct_tomorrow,
            "pct_change_week": pct_week,
            "direction": "up" if pct_tomorrow > 0 else "down",
            "confidence_interval_tomorrow": {
                "lower": round(float(tomorrow_row["yhat_lower"]), 2),
                "upper": round(float(tomorrow_row["yhat_upper"]), 2),
            },
            "confidence_interval_week": {
                "lower": round(float(week_row["yhat_lower"]), 2),
                "upper": round(float(week_row["yhat_upper"]), 2),
            }
        }

    except Exception as e:
        print(f"[Prophet] Error: {e}")
        return {"error": str(e)}