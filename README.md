# Grace Irvine Ministry Clean

The data backbone behind [Grace Irvine Ministry UI](https://github.com/Grace-Irvine/Grace-Irvine-Ministry-UI). This pipeline reads raw ministry data from Google Sheets, cleans and transforms it into structured domain models, and stores the results in Google Cloud Storage — where the MCP server picks it up to power the church's AI assistant.

**Ministry leaders just maintain their familiar Google Sheets. The AI stays accurate automatically.**

## How It Fits Together

```
┌──────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Google Sheets   │     │  Ministry-Clean   │     │   GCS Bucket    │
│  (raw ministry    │────▶│  (this repo)      │────▶│  (structured    │
│   data, managed   │     │                   │     │   domain JSON)  │
│   by church staff)│     │  Extract → Clean  │     │                 │
└──────────────────┘     │  → Transform →    │     └────────┬────────┘
                          │    Upload         │              │
                          └──────────────────┘              │
                                                             ▼
┌──────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Ministry UI     │◀────│   Gemini AI      │◀────│   MCP Server    │
│  (Next.js chat)   │     │  (function calls) │     │  (reads GCS)    │
│                   │     │                   │     │                 │
│  "Who preached    │     │  Calls MCP tools  │     │  query_sermon   │
│   last Sunday?"   │     │  for real data    │     │  query_volunteer│
└──────────────────┘     └──────────────────┘     └─────────────────┘
```

## What This Repo Does

1. **Extract** — Connects to Google Sheets via the Sheets API and reads raw ministry records (sermons, worship songs, volunteer schedules)
2. **Clean** — Normalizes dates, strips whitespace, resolves name aliases (e.g., "小明" → "Zhang Xiaoming"), validates scripture references, splits song lists by Chinese/English delimiters
3. **Transform** — Converts flat spreadsheet rows into structured domain models: `SermonDomain`, `VolunteerDomain`, `WorshipDomain` — each with metadata, date ranges, and record counts
4. **Store** — Uploads domain JSON files to a GCS bucket (`domains/sermon/latest.json`, `domains/volunteer/latest.json`, `domains/worship/latest.json`) with optional yearly/quarterly snapshots

## Data Domains

| Domain | Source Sheet | What's Captured | Output |
|---|---|---|---|
| **Sermon** | Weekly service log | Date, speaker, title, scripture, series, catechism | `domains/sermon/latest.json` |
| **Worship** | Weekly service log | Songs, worship leader, pianist, per-service history | `domains/worship/latest.json` |
| **Volunteer** | Weekly service log | All ministry roles per Sunday — sound, projection, ushers, communion, etc. | `domains/volunteer/latest.json` |

Each domain file contains:
- `metadata` — domain name, version, generation timestamp, record count, date range
- `sermons` / `volunteers` / `services` — the actual records as structured JSON arrays

## MCP Server

This repo also includes a full **MCP (Model Context Protocol) server** built with [FastMCP 2.0](https://github.com/jlowin/fastmcp), deployable as a Cloud Run service. It reads from GCS and exposes tools that the AI assistant calls:

| MCP Tool | What It Does |
|---|---|
| `query_sermon_by_date` | Look up sermon details for a specific Sunday |
| `query_volunteers_by_date` | Who served on a given date |
| `query_date_range` | Query sermons and/or volunteers across a date range |
| `get_sermons_by_preacher` | All sermons by a specific speaker |
| `get_sermon_series` | List all sermon series with episode counts |
| `get_volunteer_service_counts` | Service frequency stats by volunteer and role |
| `get_volunteer_assignments` | Full volunteer roster and roles |
| `generate_weekly_preview` | Generate a preview of next Sunday's service plan |

When a church member asks the AI *"How many times has Brother Wang served on sound this year?"*, Gemini calls `get_volunteer_service_counts` → MCP reads from GCS → returns structured data → Gemini formats a natural language answer.

## Why Google Sheets?

Church volunteers are not engineers. They already know how to use spreadsheets. This pipeline meets them where they are:

- **No new tools to learn** — Ministry coordinators keep updating the same Google Sheet they've always used
- **Automatic sync** — The cleaning pipeline runs on schedule, keeping the AI's knowledge current
- **Error tolerance** — The cleaning layer handles messy real-world data: inconsistent date formats, extra spaces, name variations, mixed Chinese/English delimiters
- **Alias resolution** — Maps informal names and nicknames to canonical identities across the entire dataset

## Project Structure

```
├── core/                    # Core pipeline modules
│   ├── clean_pipeline.py    # Main cleaning orchestrator
│   ├── gsheet_utils.py      # Google Sheets API client
│   ├── cleaning_rules.py    # Data normalization rules
│   ├── alias_utils.py       # Name alias resolution
│   ├── validators.py        # Data validation
│   ├── service_layer.py     # Domain model transformers
│   ├── cloud_storage_utils.py  # GCS upload client
│   ├── schema_manager.py    # Dynamic schema detection
│   └── change_detector.py   # Incremental change detection
├── mcp/                     # MCP server (Cloud Run)
│   ├── mcp_server.py        # FastMCP 2.0 server with all tools
│   └── Dockerfile
├── api/                     # REST API (Cloud Run)
│   ├── app.py               # Flask API for direct data access
│   └── Dockerfile
├── service/                 # Scheduler service
│   └── mcp_server.py        # Scheduled cleaning + MCP
├── config/
│   ├── config.json          # Pipeline configuration
│   └── env.example          # Environment variable template
└── deploy/                  # Cloud Build configs
```

## Setup

### Prerequisites

- Python 3.10+
- Google Cloud project with Sheets API and Cloud Storage enabled
- Service account with access to your Sheets and GCS bucket

### Local Development

```bash
# Clone
git clone https://github.com/Grace-Irvine/Grace-Irvine-Ministry-Clean.git
cd Grace-Irvine-Ministry-Clean

# Install dependencies
pip install -r requirements.txt

# Configure
cp config/env.example .env
# Edit .env with your Google Sheets ID, GCS bucket, etc.

# Run the cleaning pipeline
python core/clean_pipeline.py --config config/config.json
```

### Environment Variables

| Variable | Description |
|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON |
| `GCS_BUCKET` | GCS bucket name (default: `grace-irvine-ministry-data`) |
| `GCS_BASE_PATH` | Base path in bucket (default: `domains/`) |
| `CONFIG_PATH` | Path to `config.json` |

### Deploy MCP Server to Cloud Run

```bash
cd mcp/
gcloud run deploy ministry-data-mcp \
  --source . \
  --region us-central1 \
  --set-secrets MCP_BEARER_TOKEN=mcp-bearer-token:latest
```

## Related Repos

| Repo | Role |
|---|---|
| **[Ministry-UI](https://github.com/Grace-Irvine/Grace-Irvine-Ministry-UI)** | Next.js chat interface — the user-facing AI assistant |
| **Ministry-Clean** (this repo) | Data pipeline + MCP server — the data backbone |
| **[Ministry-Scheduler](https://github.com/Grace-Irvine/Grace-Irvine-Ministry-Scheduler)** | Automated scheduling for ministry teams |
| **[Ministry-data-visualizer](https://github.com/Grace-Irvine/Grace-Irvine-Ministry-data-visualizer)** | Data visualization dashboard |

## License

MIT
