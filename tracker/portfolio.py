from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from xml.etree import ElementTree


def _text(node: ElementTree.Element, tag: str, default: str = "") -> str:
    child = node.find(f".//{{*}}{tag}")
    if child is None or child.text is None:
        return default
    return child.text.strip()


def _number(value: str) -> float:
    if not value:
        return 0
    return float(value.replace(",", ""))


def parse_information_table(xml_text: str) -> List[dict]:
    root = ElementTree.fromstring(xml_text)
    holdings = []

    for row in root.findall(".//{*}infoTable"):
        put_call = _text(row, "putCall")
        shares = int(_number(_text(row, "sshPrnamt")))
        value_usd = int(round(_number(_text(row, "value"))))
        cusip = _text(row, "cusip").upper()

        holdings.append(
            {
                "issuer": _text(row, "nameOfIssuer"),
                "class": _text(row, "titleOfClass"),
                "cusip": cusip,
                "value_usd": value_usd,
                "shares": shares,
                "share_type": _text(row, "sshPrnamtType"),
                "put_call": put_call,
                "discretion": _text(row, "investmentDiscretion"),
                "kind": put_call.lower() if put_call else "equity",
            }
        )

    return sorted(holdings, key=lambda item: item["value_usd"], reverse=True)


def summarize_portfolio(holdings: Iterable[dict]) -> dict:
    rows = [dict(item) for item in holdings]
    total = sum(item["value_usd"] for item in rows)
    option_value = sum(item["value_usd"] for item in rows if item["put_call"])

    for item in rows:
        item["weight"] = item["value_usd"] / total if total else 0
        item["avg_reported_price"] = (
            item["value_usd"] / item["shares"]
            if item["shares"] and not item["put_call"]
            else None
        )

    return {
        "total_value_usd": total,
        "position_count": len(rows),
        "equity_count": sum(1 for item in rows if not item["put_call"]),
        "option_count": sum(1 for item in rows if item["put_call"]),
        "option_value_usd": option_value,
        "option_weight": option_value / total if total else 0,
        "top_holding": rows[0] if rows else None,
        "top_5_weight": sum(item["weight"] for item in rows[:5]),
        "holdings": rows,
    }


def classify_changes(latest: Iterable[dict], previous: Iterable[dict]) -> List[dict]:
    latest_by_key = {_position_key(item): item for item in latest}
    previous_by_key = {_position_key(item): item for item in previous}
    all_keys = set(latest_by_key) | set(previous_by_key)
    changes = []

    for key in all_keys:
        current = latest_by_key.get(key)
        prior = previous_by_key.get(key)
        reference = current or prior

        if current and not prior:
            status = "new"
            issuer = current["issuer"]
            current_value = current["value_usd"]
            previous_value = 0
            current_shares = current["shares"]
            previous_shares = 0
        elif prior and not current:
            status = "sold_out"
            issuer = prior["issuer"]
            current_value = 0
            previous_value = prior["value_usd"]
            current_shares = 0
            previous_shares = prior["shares"]
        else:
            issuer = current["issuer"]
            current_value = current["value_usd"]
            previous_value = prior["value_usd"]
            current_shares = current["shares"]
            previous_shares = prior["shares"]
            if current_shares > previous_shares:
                status = "increased"
            elif current_shares < previous_shares:
                status = "reduced"
            else:
                status = "unchanged"

        changes.append(
            {
                "key": key,
                "cusip": reference["cusip"],
                "issuer": issuer,
                "position_type": reference["put_call"] or "Equity",
                "status": status,
                "value_delta_usd": current_value - previous_value,
                "share_delta": current_shares - previous_shares,
                "current_value_usd": current_value,
                "previous_value_usd": previous_value,
            }
        )

    return sorted(changes, key=lambda item: abs(item["value_delta_usd"]), reverse=True)


def _position_key(item: dict) -> str:
    position_type = item.get("put_call") or "Equity"
    return f"{item['cusip']}|{position_type}|{item.get('class', '')}"


def attach_tickers(holdings: Iterable[dict], tickers_path: Path) -> List[dict]:
    ticker_map = {}
    if tickers_path.exists():
        ticker_map = json.loads(tickers_path.read_text())

    enriched = []
    for item in holdings:
        row = dict(item)
        row["ticker"] = ticker_map.get(row["cusip"], {}).get("ticker")
        row["sector"] = ticker_map.get(row["cusip"], {}).get("sector", "Unknown")
        enriched.append(row)
    return enriched


def build_snapshot(
    latest_meta: dict,
    latest_holdings: List[dict],
    previous_meta: Optional[dict],
    previous_holdings: Optional[List[dict]],
    tickers_path: Path,
    fetched_at: str,
) -> dict:
    latest = attach_tickers(latest_holdings, tickers_path)
    previous = attach_tickers(previous_holdings or [], tickers_path)
    summary = summarize_portfolio(latest)
    changes = classify_changes(latest, previous) if previous else []

    return {
        "manager": "Situational Awareness LP",
        "cik": "0002045724",
        "fetched_at": fetched_at,
        "latest_filing": latest_meta,
        "previous_filing": previous_meta,
        "summary": summary,
        "changes": changes,
        "source_note": "SEC 13F filings are delayed public disclosures and are not real-time trading records.",
    }
