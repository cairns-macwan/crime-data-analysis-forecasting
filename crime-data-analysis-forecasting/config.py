from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

class Settings:
    DB_URL = os.getenv("DB_URL", "sqlite:///crime.db")

settings = Settings()
