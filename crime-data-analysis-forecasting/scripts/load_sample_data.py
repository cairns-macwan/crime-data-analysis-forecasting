# scripts/load_sample_data.py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from config import settings
from models import Base, Location, Crime

def run():
    engine = create_engine(settings.DB_URL, echo=False, pool_pre_ping=True)
    Base.metadata.create_all(engine)

    seed_locations = [
        {"area": "City Centre", "city": "Cambridge", "latitude": 52.2053, "longitude": 0.1218},
        {"area": "Castle Ward", "city": "Cambridge", "latitude": 52.2140, "longitude": 0.1160},
        {"area": "Kensington", "city": "London", "latitude": 51.4990, "longitude": -0.1930}
    ]

    seed_crimes = [
        {"crime_type": "Burglary", "date": "2025-07", "outcome": "Under investigation",
         "description": "Reported house break-in", "location_area": "City Centre"},
        {"crime_type": "Anti-social behaviour", "date": "2025-07", "outcome": "No suspect identified",
         "description": "Noise complaint", "location_area": "Castle Ward"},
        {"crime_type": "Robbery", "date": "2025-08", "outcome": "Suspect charged",
         "description": "Street robbery", "location_area": "Kensington"},
        {"crime_type": "Shoplifting", "date": "2025-08", "outcome": "Under investigation",
         "description": "Retail theft", "location_area": "City Centre"}
    ]

    with Session(engine) as session:
        # upsert locations
        area_to_id = {}
        for loc in seed_locations:
            existing = session.query(Location).filter_by(area=loc["area"], city=loc["city"]).first()
            if not existing:
                existing = Location(**loc)
                session.add(existing)
                session.flush()
            area_to_id[existing.area] = existing.id

        # insert crimes
        for c in seed_crimes:
            session.add(Crime(
                crime_type=c["crime_type"],
                date=c["date"],
                outcome=c["outcome"],
                description=c["description"],
                location_id=area_to_id[c["location_area"]]
            ))
        session.commit()

    print("✅ Loaded sample data successfully.")

if __name__ == "__main__":
    run()
