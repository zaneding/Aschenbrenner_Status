from __future__ import annotations

from html import escape
from pathlib import Path


def _money(value: float) -> str:
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    return f"${value:,.0f}"


def _percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def _title(value: str) -> str:
    return value.title()


def _bar(x: int, y: int, width: int, height: int, ratio: float, fill: str) -> str:
    filled = max(4, int(width * max(0, min(ratio, 1))))
    return (
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="8" fill="#ece9df"/>'
        f'<rect x="{x}" y="{y}" width="{filled}" height="{height}" rx="8" fill="{fill}"/>'
    )


def build_svg_dashboard(snapshot: dict) -> str:
    filing = snapshot["latest_filing"]
    summary = snapshot["summary"]
    holdings = summary["holdings"][:8]
    total = summary["total_value_usd"]
    max_weight = max((holding["weight"] for holding in holdings), default=1)

    sector_totals = {}
    for holding in summary["holdings"]:
        sector = holding.get("sector") or "Unknown"
        sector_totals[sector] = sector_totals.get(sector, 0) + holding["value_usd"]
    sectors = sorted(sector_totals.items(), key=lambda item: item[1], reverse=True)[:7]
    max_sector = max((value for _, value in sectors), default=1)

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="900" viewBox="0 0 1400 900">',
        "<defs>",
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">',
        '<stop offset="0%" stop-color="#f8f7f0"/>',
        '<stop offset="100%" stop-color="#e7efe8"/>',
        "</linearGradient>",
        '<filter id="shadow"><feDropShadow dx="0" dy="18" stdDeviation="22" flood-color="#1d241f" flood-opacity="0.16"/></filter>',
        "</defs>",
        '<rect width="1400" height="900" fill="url(#bg)"/>',
        '<rect x="48" y="44" width="1304" height="812" rx="26" fill="#ffffff" filter="url(#shadow)"/>',
        '<text x="90" y="112" font-family="Avenir Next, Helvetica, Arial" font-size="24" font-weight="700" fill="#0f7a56">Situational Awareness LP / SEC 13F</text>',
        f'<text x="90" y="166" font-family="Georgia, serif" font-size="56" font-weight="700" fill="#171916">13F Dashboard {escape(filing["report_date"])}</text>',
        f'<text x="90" y="206" font-family="Avenir Next, Helvetica, Arial" font-size="20" fill="#6f726d">Filed {escape(filing["filing_date"])} · {escape(filing["accession"])} · delayed public disclosure</text>',
    ]

    cards = [
        ("Reported value", _money(total), "#2e302c"),
        ("Positions", str(summary["position_count"]), "#0f7a56"),
        ("Top 5 weight", _percent(summary["top_5_weight"]), "#188c9b"),
        ("Option exposure", _percent(summary["option_weight"]), "#b36b00"),
    ]
    for index, (label, value, color) in enumerate(cards):
        x = 90 + index * 305
        parts.extend(
            [
                f'<rect x="{x}" y="250" width="270" height="126" rx="18" fill="{color}"/>',
                f'<text x="{x + 24}" y="294" font-family="Avenir Next, Helvetica, Arial" font-size="18" fill="#ffffff" opacity="0.75">{label}</text>',
                f'<text x="{x + 24}" y="342" font-family="Avenir Next, Helvetica, Arial" font-size="36" font-weight="800" fill="#ffffff">{value}</text>',
            ]
        )

    parts.append('<text x="90" y="438" font-family="Avenir Next, Helvetica, Arial" font-size="28" font-weight="800" fill="#171916">Portfolio heat map</text>')
    y = 470
    for index, holding in enumerate(holdings, start=1):
        label = f"#{index} {_title(holding['issuer'])}"
        kind = holding.get("put_call") or "Equity"
        parts.append(f'<text x="90" y="{y + 18}" font-family="Avenir Next, Helvetica, Arial" font-size="18" font-weight="700" fill="#171916">{escape(label)}</text>')
        parts.append(f'<text x="520" y="{y + 18}" font-family="Avenir Next, Helvetica, Arial" font-size="16" fill="#6f726d">{escape(kind)} · {_money(holding["value_usd"])} · {_percent(holding["weight"])}</text>')
        parts.append(_bar(90, y + 30, 760, 18, holding["weight"] / max_weight, "#0f7a56" if not holding.get("put_call") else "#188c9b"))
        y += 46

    parts.append('<text x="930" y="438" font-family="Avenir Next, Helvetica, Arial" font-size="28" font-weight="800" fill="#171916">Sector allocation</text>')
    y = 470
    for sector, value in sectors:
        ratio = value / max_sector if max_sector else 0
        weight = value / total if total else 0
        parts.append(f'<text x="930" y="{y + 18}" font-family="Avenir Next, Helvetica, Arial" font-size="17" font-weight="700" fill="#171916">{escape(sector)}</text>')
        parts.append(f'<text x="1210" y="{y + 18}" font-family="Avenir Next, Helvetica, Arial" font-size="15" fill="#6f726d">{_percent(weight)}</text>')
        parts.append(_bar(930, y + 30, 330, 18, ratio, "#b36b00"))
        y += 52

    parts.extend(
        [
            '<rect x="90" y="805" width="1180" height="1" fill="#deded7"/>',
            '<text x="90" y="836" font-family="Avenir Next, Helvetica, Arial" font-size="16" fill="#6f726d">13F filings are delayed disclosures and do not represent live positions or trades.</text>',
            "</svg>",
        ]
    )
    return "\n".join(parts)


def write_svg_dashboard(snapshot: dict, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    accession = snapshot["latest_filing"]["accession"]
    output = output_dir / f"{accession}.svg"
    output.write_text(build_svg_dashboard(snapshot))
    return output
