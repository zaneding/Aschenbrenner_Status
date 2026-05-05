import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tracker.notion_update import check_new_filing, mark_notified
from tracker.sec_client import load_snapshot


def main():
    parser = argparse.ArgumentParser(description="Prepare Notion update only when a new 13F exists.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("--refresh", action="store_true", help="Refresh SEC data before checking.")

    mark_parser = subparsers.add_parser("mark")
    mark_parser.add_argument("accession")
    mark_parser.add_argument("--notion-target", default=None)

    args = parser.parse_args()
    data_dir = ROOT / "data"

    if args.command == "check":
        snapshot = load_snapshot(data_dir, refresh=args.refresh)
        print(json.dumps(check_new_filing(snapshot, data_dir), indent=2))
        return

    if args.command == "mark":
        print(json.dumps(mark_notified(data_dir, args.accession, args.notion_target), indent=2))


if __name__ == "__main__":
    main()
