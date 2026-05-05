from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple
from urllib.request import Request, urlopen

from tracker.portfolio import build_snapshot, parse_information_table


CIK = "0002045724"
CIK_INT = "2045724"
SUBMISSIONS_URL = f"https://data.sec.gov/submissions/CIK{CIK}.json"
ARCHIVE_ROOT = f"https://www.sec.gov/Archives/edgar/data/{CIK_INT}"
USER_AGENT = os.environ.get(
    "SEC_USER_AGENT",
    "aschenbrenner-hedge-fund-tracker/0.1 contact@example.com",
)


def _fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def _recent_13f_filings(submissions: dict, limit: int = 2) -> List[dict]:
    recent = submissions["filings"]["recent"]
    filings = []
    for index, form in enumerate(recent["form"]):
        if form != "13F-HR":
            continue
        accession = recent["accessionNumber"][index]
        filings.append(
            {
                "accession": accession,
                "accession_nodash": accession.replace("-", ""),
                "filing_date": recent["filingDate"][index],
                "report_date": recent["reportDate"][index],
                "acceptance_datetime": recent["acceptanceDateTime"][index],
                "form": form,
                "primary_document": recent["primaryDocument"][index],
                "sec_url": f"{ARCHIVE_ROOT}/{accession.replace('-', '')}/",
            }
        )
        if len(filings) == limit:
            break
    return filings


def _information_table_url(filing: dict) -> str:
    index_url = f"{ARCHIVE_ROOT}/{filing['accession_nodash']}/index.json"
    index = json.loads(_fetch_text(index_url))
    for item in index["directory"]["item"]:
        name = item["name"]
        lower = name.lower()
        if lower.endswith(".xml") and name != "primary_doc.xml":
            return f"{ARCHIVE_ROOT}/{filing['accession_nodash']}/{name}"
    raise RuntimeError(f"No information table XML found for {filing['accession']}")


def fetch_latest_snapshot(data_dir: Path) -> dict:
    submissions = json.loads(_fetch_text(SUBMISSIONS_URL))
    filings = _recent_13f_filings(submissions, limit=2)
    if not filings:
        raise RuntimeError("No 13F-HR filings found for Situational Awareness LP.")

    parsed: List[Tuple[dict, list]] = []
    for filing in filings:
        table_url = _information_table_url(filing)
        filing["information_table_url"] = table_url
        xml_text = _fetch_text(table_url)
        parsed.append((filing, parse_information_table(xml_text)))

    fetched_at = datetime.now(timezone.utc).isoformat()
    snapshot = build_snapshot(
        parsed[0][0],
        parsed[0][1],
        parsed[1][0] if len(parsed) > 1 else None,
        parsed[1][1] if len(parsed) > 1 else None,
        data_dir / "tickers.json",
        fetched_at,
    )

    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "latest.json").write_text(json.dumps(snapshot, indent=2))
    return snapshot


def load_snapshot(data_dir: Path, refresh: bool = False) -> dict:
    latest_path = data_dir / "latest.json"
    seed_path = data_dir / "seed.json"

    if refresh or not latest_path.exists():
        try:
            return fetch_latest_snapshot(data_dir)
        except Exception as exc:
            if latest_path.exists():
                snapshot = json.loads(latest_path.read_text())
                snapshot["warning"] = f"SEC refresh failed, serving cached data: {exc}"
                return snapshot
            if seed_path.exists():
                snapshot = json.loads(seed_path.read_text())
                snapshot["warning"] = f"SEC refresh failed, serving bundled seed data: {exc}"
                return snapshot
            raise

    return json.loads(latest_path.read_text())


def latest_filing_summary(data_dir: Path) -> str:
    snapshot = load_snapshot(data_dir, refresh=True)
    filing = snapshot["latest_filing"]
    total = snapshot["summary"]["total_value_usd"]
    return (
        f"{snapshot['manager']} {filing['form']} report_date={filing['report_date']} "
        f"filing_date={filing['filing_date']} total_value_usd={total}"
    )
