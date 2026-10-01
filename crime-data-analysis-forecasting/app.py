"""
app.py – Crime Analytics Dashboard (Flask + MySQL)

Routes:
  - /               → dashboard page (templates/dashboard.html)
  - /dashboard      → same as /
  - /api/summary    → totals, trend by month, top crime types
  - /api/forecast   → Prophet-based monthly forecast (reads data/predictions.json)
  - /api/hotspots   → hotspot locations (lat/lon + counts)
  - /export/csv     → download filtered crimes as CSV
  - flask db-init   → create tables if they do not exist
"""

from flask import Flask, render_template, jsonify, request, Response
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from config import settings
from models import Base, Crime, Location

from pathlib import Path
import json
from io import StringIO
import csv

# -------------------------------------------------------------------
# Flask + database setup
# -------------------------------------------------------------------

app = Flask(__name__)

# Single SQLAlchemy engine + session factory
engine = create_engine(settings.DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


# -------------------------------------------------------------------
# Helper: build base Crime query from simple filters
# (year, month, type). We deliberately DO NOT join Location here,
# so that each endpoint can decide how to join it (avoids alias bugs).
# -------------------------------------------------------------------
def build_crime_query(session, year=None, month=None, ctype=None):
    q = session.query(Crime)

    # date is stored as 'YYYY-MM'
    if year:
        q = q.filter(Crime.date.startswith(year))

    if month and month.isdigit():
        month = month.zfill(2)
        if year:
            q = q.filter(Crime.date.like(f"{year}-{month}%"))
        else:
            q = q.filter(Crime.date.like(f"%-{month}%"))

    if ctype:
        q = q.filter(Crime.crime_type.ilike(f"%{ctype}%"))

    return q


# -------------------------------------------------------------------
# CLI command: initialise DB schema
# -------------------------------------------------------------------
@app.cli.command("db-init")
def db_init():
    """Create tables if they do not exist."""
    Base.metadata.create_all(engine)
    print("✅ Database tables created (or already exist).")


# -------------------------------------------------------------------
# Page routes
# -------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# -------------------------------------------------------------------
# /api/summary – main dashboard stats
# -------------------------------------------------------------------
@app.get("/api/summary")
def api_summary():
    """
    Returns:
      {
        "total_crimes": int,
        "by_month": {"labels": [...], "counts": [...]},
        "by_type": {"labels": [...], "counts": [...]}
      }

    Optional query params:
      - year  (YYYY)
      - month (MM)
      - type  (crime type substring)
      - place (city or area substring – requires join with Location)
    """
    year = (request.args.get("year") or "").strip()
    month = (request.args.get("month") or "").strip()
    ctype = (request.args.get("type") or "").strip()
    place = (request.args.get("place") or "").strip()

    session = SessionLocal()
    try:
        # base query with year / month / type filters
        q = build_crime_query(session, year, month, ctype)

        # if place filter is set, join to locations
        if place:
            q = (
                q.join(Location)
                 .filter(
                    (Location.city.ilike(f"%{place}%")) |
                    (Location.area.ilike(f"%{place}%"))
                 )
            )

        # total crimes
        total_crimes = q.count()

        # monthly trend
        month_rows = (
            q.with_entities(Crime.date, func.count().label("cnt"))
             .group_by(Crime.date)
             .order_by(Crime.date)
             .all()
        )
        m_labels = [row[0] for row in month_rows]
        m_counts = [int(row[1]) for row in month_rows]

        # top crime types
        type_rows = (
            q.with_entities(Crime.crime_type, func.count().label("cnt"))
             .group_by(Crime.crime_type)
             .order_by(func.count().desc())
             .limit(8)
             .all()
        )
        t_labels = [row[0] for row in type_rows]
        t_counts = [int(row[1]) for row in type_rows]

        return jsonify(
            {
                "total_crimes": total_crimes,
                "by_month": {"labels": m_labels, "counts": m_counts},
                "by_type": {"labels": t_labels, "counts": t_counts},
            }
        )
    finally:
        session.close()


# -------------------------------------------------------------------
# /api/forecast – Prophet forecast (reads data/predictions.json)
# -------------------------------------------------------------------
@app.get("/api/forecast")
def api_forecast():
    """
    Returns pre-computed Prophet forecast.

    Query params:
      - horizon (int, optional): number of future points to return (default 12)

    Response:
      {
        "points": [
          {"date": "2025-01", "value": 1234.5, "lower": 1000.0, "upper": 1500.0},
          ...
        ]
      }
    """
    horizon = request.args.get("horizon", type=int) or 12

    pred_path = Path("data") / "predictions.json"
    if not pred_path.exists():
        # front-end will show a friendly message if nothing is returned
        return jsonify({"points": []})

    with pred_path.open("r", encoding="utf-8") as f:
        rows = json.load(f)

    # clean up and limit to requested horizon
    points = []
    for row in rows[:horizon]:
        points.append(
            {
                "date": row.get("date") or row.get("ds"),
                "value": float(row.get("yhat", 0)),
                "lower": float(row.get("yhat_lower", 0))
                if row.get("yhat_lower") is not None
                else None,
                "upper": float(row.get("yhat_upper", 0))
                if row.get("yhat_upper") is not None
                else None,
            }
        )

    return jsonify({"points": points})


# -------------------------------------------------------------------
# /api/hotspots – map markers for Leaflet
# -------------------------------------------------------------------
@app.get("/api/hotspots")
def api_hotspots():
    """
    Returns hotspot locations (for the Leaflet map).

    Optional filters (same as summary):
      - year, month, type, place
    """
    year = (request.args.get("year") or "").strip()
    month = (request.args.get("month") or "").strip()
    ctype = (request.args.get("type") or "").strip()
    place = (request.args.get("place") or "").strip()

    session = SessionLocal()
    try:
        q = build_crime_query(session, year, month, ctype)

        # always join locations here, we need lat/lon anyway
        q = q.join(Location)

        if place:
            q = q.filter(
                (Location.city.ilike(f"%{place}%"))
                | (Location.area.ilike(f"%{place}%"))
            )

        rows = (
            q.with_entities(
                Location.latitude,
                Location.longitude,
                Location.city,
                Location.area,
                func.count(Crime.id).label("cnt"),
            )
            .group_by(
                Location.id,
                Location.latitude,
                Location.longitude,
                Location.city,
                Location.area,
            )
            .order_by(func.count(Crime.id).desc())
            .limit(200)
            .all()
        )

        out = []
        for lat, lon, city, area, cnt in rows:
            if lat is None or lon is None:
                continue
            out.append(
                {
                    "lat": float(lat),
                    "lon": float(lon),
                    "city": city,
                    "area": area,
                    "count": int(cnt),
                }
            )

        return jsonify(out)
    finally:
        session.close()


# -------------------------------------------------------------------
# /export/csv – filtered CSV export
# -------------------------------------------------------------------
@app.get("/export/csv")
def export_csv():
    """
    Export crimes as CSV.

    Columns:
      date, crime_type, area, city, latitude, longitude, outcome
    """
    year = (request.args.get("year") or "").strip()
    month = (request.args.get("month") or "").strip()
    ctype = (request.args.get("type") or "").strip()
    place = (request.args.get("place") or "").strip()

    session = SessionLocal()
    try:
        q = build_crime_query(session, year, month, ctype)

        # join Location exactly once – this avoids the "Not unique table/alias" error
        q = q.join(Location)

        if place:
            q = q.filter(
                (Location.city.ilike(f"%{place}%"))
                | (Location.area.ilike(f"%{place}%"))
            )

        q = q.with_entities(
            Crime.date,
            Crime.crime_type,
            Location.area,
            Location.city,
            Location.latitude,
            Location.longitude,
            Crime.outcome,
        )

        # build CSV in memory
        si = StringIO()
        writer = csv.writer(si)
        writer.writerow(
            ["date", "crime_type", "area", "city", "latitude", "longitude", "outcome"]
        )

        # safety cap to avoid dumping millions of rows by accident
        for row in q.limit(50000):
            writer.writerow(
                [
                    row[0],
                    row[1],
                    row[2] or "",
                    row[3] or "",
                    row[4] if row[4] is not None else "",
                    row[5] if row[5] is not None else "",
                    row[6] or "",
                ]
            )

        output = si.getvalue()
        headers = {
            "Content-Disposition": "attachment; filename=crime_export.csv"
        }
        return Response(output, mimetype="text/csv", headers=headers)
    finally:
        session.close()


# -------------------------------------------------------------------
# Legacy simple stats endpoint (still used by old bits of code)
# -------------------------------------------------------------------
@app.get("/api/stats")
def api_stats():
    """Very small endpoint: just returns total crimes for year + type."""
    year = (request.args.get("year") or "").strip()
    ctype = (request.args.get("type") or "").strip()

    session = SessionLocal()
    try:
        q = build_crime_query(session, year, None, ctype)
        return jsonify({"total_crimes": q.count()})
    finally:
        session.close()


# -------------------------------------------------------------------
# Development entry point
# -------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)

