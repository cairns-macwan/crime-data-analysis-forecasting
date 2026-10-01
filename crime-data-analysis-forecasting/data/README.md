# Data

Obtain street-level CSV data from UK Police Open Data: https://data.police.uk/data/
Review the provider's current terms and attribution requirements before redistributing datasets.

The local source project contained 168 CSV files named for September 2022 through December 2024 across Cambridgeshire, Merseyside, Metropolitan, Thames Valley, West Midlands and West Yorkshire police forces. File names describe the available source collection, not a verified database import count.

Place downloaded CSVs in data/ukpolice/raw/ and run the importer from the repository root. This repository excludes those large downloads and all local database files.

The sample loader creates four fictional records for testing. Keep these separate from real observations and forecasting data.

Forecast training writes predictions.json here; regenerate it locally rather than publishing stale results.
