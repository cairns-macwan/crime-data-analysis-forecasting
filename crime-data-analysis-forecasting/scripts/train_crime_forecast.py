import pandas as pd
import json
from sqlalchemy import create_engine
import sys
import os

# Make project root importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

from config import settings
from models import Crime
from sqlalchemy.orm import sessionmaker
from prophet import Prophet  # pip install prophet
import warnings
warnings.filterwarnings("ignore")


def load_monthly_crime_data():
    engine = create_engine(settings.DB_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    print("📌 Loading crime data from MySQL...")

    rows = (
        session.query(Crime.date)
        .all()
    )

    session.close()

    if not rows:
        print("❌ No crime records found in database!")
        return None

    # Convert to dataframe
    df = pd.DataFrame(rows, columns=["date"])
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m")

    # Count per month
    monthly = df.groupby("date").size().reset_index(name="crimes")

    monthly = monthly.rename(columns={
        "date": "ds",
        "crimes": "y"
    })

    print("📌 Loaded", len(monthly), "months of crime data")
    return monthly


def train_forecast_model(df):
    print("📌 Training Prophet forecasting model...")

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
    )
    
    model.fit(df)

    print("📌 Model trained successfully!")

    # Forecast next 12 months
    future = model.make_future_dataframe(periods=12, freq="M")
    forecast = model.predict(future)

    results = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(12)

    return results


def save_predictions(results):
    out_file = "data/predictions.json"

    results["ds"] = results["ds"].astype(str)

    with open(out_file, "w") as f:
        json.dump(results.to_dict(orient="records"), f, indent=4)

    print(f"✔ Predictions saved to {out_file}")


def main():
    df = load_monthly_crime_data()

    if df is None:
        return

    results = train_forecast_model(df)
    save_predictions(results)


if __name__ == "__main__":
    main()
