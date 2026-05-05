from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


STATE_FILE = "notion_state.json"
UPDATES_DIR = "notion_updates"


def _money(value: float) -> str:
    return f"${value:,.0f}"


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _title_case(value: str) -> str:
    return value.title()


def _state_path(data_dir: Path) -> Path:
    return data_dir / STATE_FILE


def load_state(data_dir: Path) -> dict:
    path = _state_path(data_dir)
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def mark_notified(data_dir: Path, accession: str, notion_target: Optional[str] = None) -> dict:
    data_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "last_notified_accession": accession,
        "notified_at": datetime.now(timezone.utc).isoformat(),
    }
    if notion_target:
        state["notion_target"] = notion_target
    _state_path(data_dir).write_text(json.dumps(state, indent=2))
    return state


def build_notion_markdown(snapshot: dict) -> str:
    filing = snapshot["latest_filing"]
    summary = snapshot["summary"]
    holdings = summary["holdings"][:10]
    changes = [change for change in snapshot.get("changes", []) if change["status"] != "unchanged"][:10]

    lines = [
        f"# Situational Awareness LP 13F Update - {filing['report_date']}",
        "",
        f"- Filing: {filing['form']} / {filing['accession']}",
        f"- Filing date: {filing['filing_date']}",
        f"- Report date: {filing['report_date']}",
        f"- Reported value: {_money(summary['total_value_usd'])}",
        f"- Positions: {summary['position_count']}",
        f"- Top 5 weight: {_percent(summary['top_5_weight'])}",
        f"- Option exposure: {_percent(summary['option_weight'])}",
        f"- SEC source: {filing['sec_url']}",
        "",
        "## Top holdings",
        "",
        "| Holding | Ticker | Type | Value | Weight | Shares |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]

    for holding in holdings:
        position_type = holding.get("put_call") or "Equity"
        lines.append(
            "| {issuer} | {ticker} | {position_type} | {value} | {weight} | {shares:,} |".format(
                issuer=_title_case(holding["issuer"]),
                ticker=holding.get("ticker") or "",
                position_type=position_type,
                value=_money(holding["value_usd"]),
                weight=_percent(holding["weight"]),
                shares=holding["shares"],
            )
        )

    lines.extend(["", "## Quarter-over-quarter changes", ""])

    if changes:
        lines.extend(
            [
                "| Change | Holding | Type | Value delta | Share delta |",
                "| --- | --- | --- | ---: | ---: |",
            ]
        )
        for change in changes:
            lines.append(
                "| {status} | {issuer} | {position_type} | {value_delta} | {share_delta:,} |".format(
                    status=change["status"],
                    issuer=_title_case(change["issuer"]),
                    position_type=change.get("position_type", ""),
                    value_delta=_money(change["value_delta_usd"]),
                    share_delta=change["share_delta"],
                )
            )
    else:
        lines.append("No previous 13F comparison is available.")

    lines.extend(
        [
            "",
            "> 13F filings are delayed public disclosures. This is not a real-time position or trade feed.",
        ]
    )
    return "\n".join(lines) + "\n"


def check_new_filing(snapshot: dict, data_dir: Path) -> dict:
    data_dir.mkdir(parents=True, exist_ok=True)
    accession = snapshot["latest_filing"]["accession"]
    state = load_state(data_dir)

    if state.get("last_notified_accession") == accession:
        return {
            "has_new_filing": False,
            "accession": accession,
            "markdown_path": None,
            "message": "No new 13F filing since last Notion update.",
        }

    updates_dir = data_dir / UPDATES_DIR
    updates_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = updates_dir / f"{accession}.md"
    markdown_path.write_text(build_notion_markdown(snapshot))

    return {
        "has_new_filing": True,
        "accession": accession,
        "markdown_path": str(markdown_path),
        "message": f"New 13F filing detected: {accession}",
    }
