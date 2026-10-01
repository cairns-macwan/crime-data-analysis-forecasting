# scripts/import_uk_police_csv.py

import os, sys, glob
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# --- Make sure we can import from project root ---
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# -------------------------------------------------

from models import Base, Location, Crime
from config import settings

load_dotenv()


# Helper function to safely convert NaN → None
def to_float_or_none(x):
    if pd.isna(x) or x == "" or x is None:
        return None
    try:
        return float(x)
    except Exception:
        return None


# Required columns from UK Police CSV
REQUIRED_COLS = {
    "Month", "Crime type", "Last outcome category", "Location",
    "Latitude", "Longitude", "LSOA name", "Falls within"
}


def load_csv_to_db(path_glob: str):
    engine = create_engine(settings.DB_URL, echo=False, pool_pre_ping=True)
    Base.metadata.create_all(engine)

    files = glob.glob(path_glob)
    if not files:
        print(f"⚠️ No files matched {path_glob}")
        return

    total_inserted = 0
    with Session(engine) as session:
        for fpath in files:
            print(f"\n📂 Importing {fpath} ...")
            try:
                df = pd.read_csv(fpath)
            except Exception as e:
                print(f"❌ Failed to read {fpath}: {e}")
                continue

            missing = REQUIRED_COLS - set(df.columns)
            if missing:
                print(f"⏭️ Skipping (missing columns: {missing})")
                continue

            # Fill NaNs for text columns
            df = df.fillna({
                "LSOA name": "",
                "Last outcome category": "",
                "Location": "",
                "Falls within": "",
            })

            for _, row in df.iterrows():
                area = (row["LSOA name"] or row["Location"] or "Unknown").strip()
                city = str(row["Falls within"]).strip() or "Unknown force"

                # safely parse coordinates
                lat = to_float_or_none(row["Latitude"])
                lon = to_float_or_none(row["Longitude"])

                # upsert location
                loc = session.query(Location).filter_by(area=area, city=city).first()
                if not loc:
                    loc = Location(area=area, city=city, latitude=lat, longitude=lon)
                    session.add(loc)
                    session.flush()  # ensure loc.id is available

                # add crime entry
                crime = Crime(
                    crime_type=str(row["Crime type"]).strip(),
                    date=str(row["Month"]).strip(),
                    outcome=str(row["Last outcome category"]).strip(),
                    description=str(row["Location"]).strip(),
                    location_id=loc.id
                )
                session.add(crime)
                total_inserted += 1

        session.commit()

    print(f"\n✅ Successfully imported {total_inserted} rows from {len(files)} file(s).")


if __name__ == "__main__":
    pattern = sys.argv[1] if len(sys.argv) > 1 else r"data\ukpolice\raw\*.csv"
    load_csv_to_db(pattern)
