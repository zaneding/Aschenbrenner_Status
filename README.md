# Aschenbrenner Status

一个本地优先的 Situational Awareness LP 公开 13F 追踪器。项目会从 SEC EDGAR 拉取 CIK `0002045724` 的最新 13F-HR filing，解析 information table，生成现代化 dashboard，并在每日检查时只对“新 13F”生成 Notion 追踪记录。

> 重要限制：13F 是延迟披露文件，不是实时交易记录，也不代表当前持仓。

## 功能

- `SEC 官方数据源`：读取 `https://data.sec.gov/submissions/CIK0002045724.json`，再下载对应 filing archive 里的 13F information table XML。
- `持仓 dashboard`：展示报告持仓市值、持仓数量、Top 5 集中度、期权暴露、持仓地图、行业分布、季度变化和可搜索持仓表。
- `季度变化识别`：与上一份 13F 比较，标记新增、增持、减持、清仓。
- `每日检查`：脚本可每天运行一次，刷新 `data/latest.json`。
- `Notion 追踪流`：只有发现新的 13F accession 时，才生成一份可视化 Notion 子页面内容；写入 Notion 成功后再标记已通知，避免重复写入。
- `无第三方运行依赖`：后端、解析、测试都使用 Python 标准库；前端是静态 HTML/CSS/JS。

## 项目结构

```text
.
├── public/                 # dashboard 前端
├── tracker/                # SEC 拉取、13F 解析、Notion 更新草稿逻辑
├── scripts/                # 手动/定时任务入口
├── tests/                  # unittest 测试
├── data/latest.json        # 最新公开 13F 缓存，方便离线首屏展示
├── data/tickers.json       # CUSIP 到 ticker/sector 的本地映射
└── server.py               # 本地 HTTP 服务
```

## Run

```bash
python3 server.py
```

Open `http://127.0.0.1:8787`.

页面右上角的“刷新 SEC”会调用 `/api/portfolio?refresh=1`，重新拉取 SEC 数据并更新本地缓存。

## Refresh Data

```bash
python3 scripts/daily_check.py
```

The script pulls the latest SEC submissions for CIK `0002045724`, downloads the newest 13F information table, compares it with the previous 13F, and writes `data/latest.json`.

For daily local automation, add this to crontab. This example runs every day at 08:15:

```cron
15 8 * * * cd /Users/zijian/Stampen/aschenbrenner-hedge-fund-tracker && /usr/bin/python3 scripts/daily_check.py >> data/daily.log 2>&1
```

## Notion Update Flow

Prepare a Notion entry only when a new 13F accession appears:

```bash
python3 scripts/check_notion_update.py check --refresh
```

If the output has `"has_new_filing": true`, create a child page under your private Notion tracking page. Use the returned `"page_title"` as the child page title and the generated markdown file as the child page content. After the child page is created successfully, mark that accession as notified:

```bash
python3 scripts/check_notion_update.py mark 0002045724-26-000002 --notion-target "YOUR_PRIVATE_NOTION_PAGE_OR_URL"
```

This two-step flow avoids marking a filing as delivered before Notion write succeeds. Each generated child page contains a visual Notion report with colored sections, KPI blocks, holding weight bars, sector allocation, and a quarter-over-quarter change matrix.

The generated markdown is written under `data/notion_updates/` and intentionally ignored by git because it is runtime output. Keep private Notion page names and URLs in local automation config, not in the public repository.

## Current Public Filing Snapshot

The bundled `data/latest.json` currently reflects the latest public SEC 13F available when this project was created:

- Manager: `Situational Awareness LP`
- CIK: `0002045724`
- Form: `13F-HR`
- Report date: `2025-12-31`
- Filing date: `2026-02-11`
- Reported value: `$5,516,758,345`
- Positions: `29`

Use `python3 scripts/daily_check.py` to refresh this snapshot.

## SEC User Agent

Set a descriptive SEC user agent if you want:

```bash
export SEC_USER_AGENT="your-name 13f tracker your-email@example.com"
```

## Notes

13F filings are delayed disclosures. They show public report-date holdings, not live trades or current positions.
