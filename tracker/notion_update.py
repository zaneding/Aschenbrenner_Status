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


def _bar(value: float, max_value: float, width: int = 18) -> str:
    if max_value <= 0:
        filled = 0
    else:
        filled = max(1, round((value / max_value) * width))
    return "[" + ("#" * filled).ljust(width, ".") + "]"


def _status_label(status: str) -> str:
    labels = {
        "new": "NEW",
        "increased": "UP",
        "reduced": "DOWN",
        "sold_out": "SOLD OUT",
        "unchanged": "FLAT",
    }
    return labels.get(status, status.upper())


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


def build_notion_child_page_title(snapshot: dict) -> str:
    filing = snapshot["latest_filing"]
    return f"13F {filing['report_date']} - {filing['accession']}"


def build_notion_markdown(snapshot: dict) -> str:
    filing = snapshot["latest_filing"]
    summary = snapshot["summary"]
    holdings = summary["holdings"][:10]
    changes = [change for change in snapshot.get("changes", []) if change["status"] != "unchanged"][:10]
    total = summary["total_value_usd"]
    equity_count = summary.get("equity_count", sum(1 for holding in summary["holdings"] if not holding.get("put_call")))
    option_count = summary.get("option_count", sum(1 for holding in summary["holdings"] if holding.get("put_call")))
    max_weight = max((holding["weight"] for holding in holdings), default=0)
    sector_totals = {}
    for holding in summary["holdings"]:
        sector = holding.get("sector") or "Unknown"
        sector_totals[sector] = sector_totals.get(sector, 0) + holding["value_usd"]
    max_sector_value = max(sector_totals.values(), default=0)

    lines = [
        f"# 13F Dashboard - {filing['report_date']} {{color=\"green\"}}",
        "",
        "> Public 13F snapshot. This is delayed disclosure, not a real-time trade feed.",
        "",
        "## KPI strip {color=\"blue\"}",
        "",
        f"- Reported value: {_money(total)}",
        f"- Positions: {summary['position_count']} total rows, {equity_count} equity / {option_count} option rows",
        f"- Top 5 weight: {_percent(summary['top_5_weight'])} {_bar(summary['top_5_weight'], 1)}",
        f"- Option exposure: {_percent(summary['option_weight'])} {_bar(summary['option_weight'], 1)}",
        f"- Filing: {filing['accession']} filed {filing['filing_date']} for report date {filing['report_date']}",
        f"- SEC source: {filing['sec_url']}",
        "",
        "## Portfolio heat map {color=\"green\"}",
        "",
    ]

    for index, holding in enumerate(holdings, start=1):
        position_type = holding.get("put_call") or "Equity"
        lines.append(
            "- #{rank} {issuer} ({position_type}): {weight} / {value} / {shares:,} shares {bar}".format(
                rank=index,
                issuer=_title_case(holding["issuer"]),
                position_type=position_type,
                value=_money(holding["value_usd"]),
                weight=_percent(holding["weight"]),
                bar=_bar(holding["weight"], max_weight),
                shares=holding["shares"],
            )
        )

    lines.extend(
        [
            "",
            "## Sector allocation {color=\"orange\"}",
            "",
        ]
    )

    for sector, value in sorted(sector_totals.items(), key=lambda item: item[1], reverse=True)[:10]:
        weight = value / total if total else 0
        lines.append(f"- {sector}: {_percent(weight)} / {_money(value)} {_bar(value, max_sector_value)}")

    lines.extend(["", "## Quarter-over-quarter change matrix {color=\"red\"}", ""])

    if changes:
        max_abs_delta = max(abs(change["value_delta_usd"]) for change in changes)
        for change in changes:
            lines.append(
                "- {status} {issuer} ({position_type}): value {value_delta}, shares {share_delta:,} {bar}".format(
                    status=_status_label(change["status"]),
                    issuer=_title_case(change["issuer"]),
                    position_type=change.get("position_type", ""),
                    value_delta=_money(change["value_delta_usd"]),
                    share_delta=change["share_delta"],
                    bar=_bar(abs(change["value_delta_usd"]), max_abs_delta),
                )
            )
    else:
        lines.append("No previous 13F comparison is available.")

    lines.extend(
        [
            "",
            "## Source and caveat {color=\"gray\"}",
            "",
            f"- SEC filing: {filing['sec_url']}",
            f"- Fetched at: {snapshot['fetched_at']}",
            "- 13F filings are delayed public disclosures. They do not show live positions, intraday trades, short positions, or complete non-US holdings.",
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
            "page_title": build_notion_child_page_title(snapshot),
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
        "page_title": build_notion_child_page_title(snapshot),
        "markdown_path": str(markdown_path),
        "message": f"New 13F filing detected: {accession}. Create a Notion child page with page_title.",
    }
