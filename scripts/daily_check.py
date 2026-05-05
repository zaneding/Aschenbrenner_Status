from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tracker.sec_client import latest_filing_summary


if __name__ == "__main__":
    print(latest_filing_summary(ROOT / "data"))
