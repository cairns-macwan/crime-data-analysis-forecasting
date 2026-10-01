# Crime Data Analysis & Forecasting

A Python and Flask portfolio project for exploring UK Police street-level crime data through monthly trends, category breakdowns, area markers and CSV exports. An experimental Prophet script generates an overall monthly forecast.

## Features and technologies

- Flask endpoints with SQLAlchemy models and MySQL/PyMySQL connectivity
- Optional SQLite configuration for a small local demonstration
- Filters for year, month, crime type and place
- Chart.js charts, Leaflet map and Bootstrap layout
- CSV import with pandas and filtered CSV export (maximum 50,000 records)
- Experimental Prophet forecasting; accuracy has not been validated

## Quick local demo (Windows Command Prompt)

Run these commands from the repository root with Python installed:

```cmd
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\python.exe -m flask --app app db-init
.venv\Scripts\python.exe run_loader.py
.venv\Scripts\python.exe -m flask --app app run --no-debugger --no-reload --port 5055
```

Open http://127.0.0.1:5055. Keep the terminal running. This demo inserts four fictional records and is not suitable for forecast training. Run the sample loader only once: repeated runs duplicate records.

## MySQL and real data

Create an empty MySQL database and a user with appropriate access. Set DB_URL in your private .env file using the commented template in .env.example. URL-encode special characters in credentials. MySQL must be running; Apache is not required to serve Flask.

Use a separate database from the fictional demo. From the repository root:

```cmd
.venv\Scripts\python.exe -m flask --app app db-init
.venv\Scripts\python.exe -m scripts.import_uk_police_csv "data/ukpolice/raw/*.csv"
```

The importer does not deduplicate crime records. Import each file only once; large imports may take considerable time. Raw data, credentials and local databases are deliberately excluded from Git.

## Experimental forecast

After importing sufficient real monthly history:

```cmd
.venv\Scripts\python.exe -m scripts.train_crime_forecast
```

This writes data/predictions.json. Without it, the forecast endpoint returns no points. Generated predictions are excluded from Git. Dependency versions are not locked; this cleaned package still needs a fresh-environment smoke test.

## Structure

```text
app.py                   Flask routes
config.py                Environment-based settings
models.py                Crime and location tables
run_loader.py            Fictional demo loader entry point
scripts/                 Demo loader, CSV importer and forecast training
templates/              Dashboard HTML (with embedded CSS and JavaScript)
data/                    Data instructions; generated/downloaded files ignored
```

## Known limitations

- The forecast uses all records, while dashboard history can be filtered. Do not interpret it as a forecast for a selected place or category.
- Forecast training uses month-start observations but currently creates month-end future dates; this needs correction before evaluating results.
- No held-out forecast accuracy results or baseline comparison are available.
- The importer stores police-force names in the city field and combines locations by area and force, retaining the first coordinates. Markers are area aggregates, not exact incident locations or a validated clustering model.
- Missing months and fictional demonstration data must be addressed before training.
- Database failures may leave blank panels; user-facing error handling needs improvement.
- Map popup text and spreadsheet exports need further hardening before accepting untrusted datasets in a public deployment.
- The frontend uses external CDNs, fonts and map tiles and therefore needs internet access.

## Data and attribution

See data/README.md. This is an educational portfolio project, not an operational crime-risk prediction service. Do not infer individual risk or exact incident locations from its output.

