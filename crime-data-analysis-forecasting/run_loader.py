import sys
from pathlib import Path

# ensure the current directory (project root) is on the Python path
sys.path.append(str(Path(__file__).resolve().parent))

from scripts.load_sample_data import run

if __name__ == "__main__":
    run()
