# Grace Irvine Ministry Data Management System

> **Language / 语言**: [English](README.md) | [中文](docs/README_CH.md)

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.118+-green.svg)](https://fastapi.tiangolo.com/)
[![MCP](https://img.shields.io/badge/MCP-1.16+-purple.svg)](https://modelcontextprotocol.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A complete church ministry data management system featuring intelligent data cleaning, domain model transformation, RESTful API, and **AI Assistant Integration via Model Context Protocol (MCP)**.

---

## Table of Contents

- [✨ Overview](#-overview)
- [🏗️ Architecture](#️-architecture)
- [🚀 Quick Start](#-quick-start)
- [📚 Documentation](#-documentation)
- [🔑 Key Features](#-key-features)
- [🛠️ Technology Stack](#️-technology-stack)
- [📦 Project Structure](#-project-structure)
- [💡 Usage Examples](#-usage-examples)
- [🧪 Testing](#-testing)
- [🤝 Contributing](#-contributing)

---

## ✨ Overview

The **Grace Irvine Ministry Data Management System** is a production-ready, AI-native application designed to:

1. **Clean and standardize** raw ministry data from Google Sheets
2. **Transform** flat data into structured domain models (Sermon + Volunteer domains)
3. **Serve** data via RESTful API endpoints for analytics and applications
4. **Enable AI integration** through the Model Context Protocol (MCP)
5. **Deploy seamlessly** to Google Cloud Run with automated scheduling

### What Makes This Special?

- **🤖 AI-Native Design**: Built-in MCP server for natural language queries with Claude, ChatGPT, and other AI assistants
- **🏗️ Clean Architecture**: 2-layer design (cleaning + service layer) with 80%+ code reuse
- **☁️ Cloud-Ready**: Containerized microservices, auto-scaling, minimal cost (~$1/month)
- **⚡ Smart Optimization**: Change detection, parallel processing, incremental updates
- **📦 Packable**: One-click installation to Claude Desktop via MCPB package

---

## 🏗️ Architecture

### Monorepo with Independent Microservices

```
Grace-Irvine-Ministry-Clean/
├── api/          # API Service - Data cleaning & REST API (FastAPI)
├── mcp/          # MCP Service - AI assistant integration (MCP Protocol)
├── core/         # Shared business logic (80%+ code reuse)
├── deploy/       # Deployment scripts
└── config/       # Configuration files
```

### Two Independent Services

| Service               | Purpose                                            | Tech Stack        | Port | Deployment |
| --------------------- | -------------------------------------------------- | ----------------- | ---- | ---------- |
| **API Service** | Data cleaning, REST API, statistics                | FastAPI + Uvicorn | 8080 | Cloud Run  |
| **MCP Service** | AI assistant integration, natural language queries | MCP SDK + FastAPI | 8080 | Cloud Run  |

Both services can run **independently** while sharing the `core/` business logic.

### 2-Layer Clean Architecture

#### Layer 1: Cleaning Layer

**Purpose**: Standardize raw data from Google Sheets

**File**: [core/clean_pipeline.py](core/clean_pipeline.py)

**Transformations**:

- Date normalization (multiple formats → YYYY-MM-DD)
- Text cleaning (strip spaces, handle placeholders)
- Alias mapping (multiple names → unified person_id)
- Song splitting (multiple delimiters)
- Scripture formatting (add space between book and chapter)
- Column merging (worship_team_1 + worship_team_2 → worship_team list)
- Data validation (required fields, duplicates, format checks)

**Output**: 29-field standardized schema written to Google Sheets "CleanData" tab

#### Layer 2: Service Layer

**Purpose**: Transform flat cleaned data into structured domain models

**File**: [core/service_layer.py](core/service_layer.py)

**Domains**:

1. **Sermon Domain** - Sermon metadata with preacher and songs

   ```json
   {
     "service_date": "2024-01-07",
     "sermon": {
       "title": "Gospel Series Part 1",
       "series": "Encountering Jesus",
       "scripture": "Genesis 3"
     },
     "preacher": {"id": "person_6511_wangtong", "name": "Wang Tong"},
     "songs": ["Amazing Grace", "Assurance"]
   }
   ```
2. **Volunteer Domain** - Volunteer assignments by role

   ```json
   {
     "service_date": "2024-01-07",
     "worship": {
       "lead": {"id": "person_xiem", "name": "Xie Miao"},
       "team": [{"id": "person_quixiaohuan", "name": "Qu Xiaohuan"}],
       "pianist": {"id": "person_shawn", "name": "Shawn"}
     },
     "technical": {
       "audio": {"id": "person_3850_jingzheng", "name": "Jing Zheng"},
       "video": {"id": "person_2012_junxin", "name": "Jun Xin"}
     }
   }
   ```

**Output**: JSON files organized by domain and year, optionally uploaded to Google Cloud Storage

### Complete Data Flow

```
Raw Data (Google Sheets)
    ↓
Cleaning Pipeline
    ├── Date normalization
    ├── Text cleanup
    ├── Alias mapping
    ├── Song splitting
    └── Validation
    ↓
Cleaned Data (Google Sheets + Local JSON/CSV)
    ↓
Service Layer Transformer
    ├── Sermon Domain Model
    └── Volunteer Domain Model
    ↓
Domain Storage
    ├── Local: logs/service_layer/{domain}_latest.json
    ├── Yearly: logs/service_layer/{year}/{domain}_{year}.json
    └── Cloud: gs://bucket/domains/{domain}/{files}
    ↓
Access Layer
    ├── REST API (api/app.py)
    ├── MCP Resources (mcp/mcp_server.py)
    └── AI Assistants (Claude, ChatGPT)
```

---

## 🚀 Quick Start

### Option 1: AI Assistant Integration (Recommended) 🤖

Integrate with Claude Desktop or ChatGPT using the MCP protocol:

**For Claude Desktop (stdio mode)**:

```bash
# Run MCP server locally
python mcp/mcp_server.py
```

**For Cloud Deployment (HTTP/SSE mode)**:

```bash
# Deploy to Cloud Run
./deploy/deploy-mcp.sh
```

**Features**:

- Natural language queries
- Pre-defined analysis prompts
- 9 tools for data operations
- 22+ resources for data access

👉 **See**: [MCP Server Documentation](mcp/README.md) | [MCP Architecture](docs/MCP_DESIGN.md)

---

### Option 2: Local Data Cleaning

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure service account
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"

# 3. Edit configuration
vim config/config.json

# 4. Test with dry-run mode
python core/clean_pipeline.py --config config/config.json --dry-run

# 5. Run cleaning pipeline
python core/clean_pipeline.py --config config/config.json
```

👉 **See**: [Quick Start Guide](docs/QUICKSTART.md)

---

### Option 3: Cloud Deployment

Deploy API and MCP services to Google Cloud Run:

```bash
# Set GCP project ID
export GCP_PROJECT_ID=your-project-id

# Deploy all services
./deploy/deploy-all.sh
```

**Features**:

- Auto-scaling based on traffic
- Scheduled updates (every 30 minutes)
- Low cost (~$1/month in free tier)
- Bearer token authentication

👉 **See**: [Cloud Deployment Guide](docs/DEPLOYMENT.md)

---

## 📚 Documentation

### Core Documentation

- [📖 Architecture Overview](docs/ARCHITECTURE.md) - System design and components
- [📝 API Endpoints](docs/API_ENDPOINTS.md) - Complete REST API reference
- [📦 Service Layer Design](docs/SERVICE_LAYER.md) - Domain model transformation
- [📋 Schema Management](docs/SCHEMA_MANAGEMENT.md) - Dynamic column mapping

### AI Integration (MCP)

- [🤖 MCP Server Guide](mcp/README.md) - Complete MCP usage guide
- [🏗️ MCP Design Document](docs/MCP_DESIGN.md) - Detailed architecture
- [☁️ MCP Cloud Deployment](docs/MCP_DEPLOYMENT.md) - Cloud Run setup
- [🔍 MCP Inspector Guide](docs/MCP_INSPECTOR.md) - Debugging tool

### Deployment & Operations

- [☁️ Cloud Deployment](docs/DEPLOYMENT.md) - Cloud Run + Scheduler setup
- [💾 Storage Management](docs/STORAGE.md) - Google Cloud Storage configuration
- [🔐 Secret Management](docs/SECRET_MANAGEMENT.md) - Secret Manager best practices
- [📋 Secrets Inventory](docs/SECRETS_INVENTORY.md) - Complete secrets list and operations
- [🔧 Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions

---

## 🔑 Key Features

### 🤖 AI Assistant Integration (MCP Protocol)

**9 Tools** (Action-oriented operations):

- `query_volunteers_by_date` - Query volunteer assignments
- `query_sermon_by_date` - Query sermon information
- `query_date_range` - Query across date ranges
- `clean_ministry_data` - Trigger cleaning pipeline
- `generate_service_layer` - Generate domain models
- `validate_raw_data` - Validate data quality
- `sync_from_gcs` - Sync from cloud storage
- `check_upcoming_completeness` - Check future scheduling
- `generate_weekly_preview` - Generate weekly preview

**22+ Resources** (Read-only data access):

- `ministry://sermon/records/{year}` - Sermon records
- `ministry://sermon/by-preacher/{name}` - Sermons by preacher
- `ministry://volunteer/assignments/{date}` - Volunteer assignments
- `ministry://volunteer/by-person/{id}` - Service history
- `ministry://stats/summary` - Overall statistics

**12+ Prompts** (Pre-defined analysis templates):

- `analyze_preaching_schedule` - Analyze sermon patterns
- `analyze_volunteer_balance` - Check service load balance
- `find_scheduling_gaps` - Find unfilled positions
- `suggest_preacher_rotation` - Suggest preacher schedule
- `check_data_quality` - Data quality assessment

**Dual Transport Modes**:

- **stdio**: For Claude Desktop local integration (no network overhead)
- **HTTP/SSE**: For cloud integration with remote clients

---

### 📊 Data Management

**Intelligent Cleaning**:

- Date normalization (multiple formats → YYYY-MM-DD)
- Text cleaning (spaces, placeholders, standardization)
- Alias mapping (multiple names → unified person_id)
- Song splitting and deduplication
- Scripture formatting
- Column merging
- Comprehensive validation

**Service Layer Transformation**:

- Sermon domain model (sermons, preachers, songs)
- Volunteer domain model (roles, assignments, availability)
- Yearly partitioning (2024-2026+)
- Cloud Storage backup (Google Cloud Storage)

**Change Detection**:

- SHA-256 hash comparison
- Skip processing if no changes detected
- 99%+ faster on repeated runs
- Reduces API calls and costs

---

### ☁️ Cloud Deployment

**API Service**:

- Complete REST API for data access
- Data cleaning endpoints
- Statistics and analytics
- Bearer token authentication
- Auto-scaling (1GB memory, max 3 instances)

**MCP Service**:

- HTTP/SSE endpoint for MCP protocol
- Remote AI assistant integration
- Bearer token authentication
- Auto-scaling (512MB memory, max 10 instances)

**Scheduling**:

- Cloud Scheduler triggers every 30 minutes
- Change detection prevents unnecessary runs
- Automated data updates

**Cost Optimization**:

- Within Google Cloud free tier (~$1/month)
- Pay-per-use pricing
- Smart caching and optimization

---

## 🛠️ Technology Stack

### Backend Framework

| Component                 | Technology    | Version | Purpose                |
| ------------------------- | ------------- | ------- | ---------------------- |
| **API Framework**   | FastAPI       | 0.118+  | Async HTTP endpoints   |
| **ASGI Server**     | Uvicorn       | 0.37+   | Production server      |
| **MCP SDK**         | mcp (Python)  | 1.16+   | Model Context Protocol |
| **SSE Transport**   | sse-starlette | 2.0+    | Server-Sent Events     |
| **Data Processing** | Pandas        | 2.2+    | DataFrame operations   |
| **Type Validation** | Pydantic      | 2.12+   | Data models            |

### Google Cloud Integration

| Component                   | Technology                      | Purpose                  |
| --------------------------- | ------------------------------- | ------------------------ |
| **Google Sheets API** | google-api-python-client 2.149+ | Read/write data          |
| **Cloud Storage**     | google-cloud-storage 2.10+      | File storage             |
| **Authentication**    | google-auth 2.34+               | OAuth2, service accounts |

### Infrastructure & Deployment

| Component                  | Technology       | Purpose            |
| -------------------------- | ---------------- | ------------------ |
| **Containerization** | Docker           | Container images   |
| **Cloud Hosting**    | Google Cloud Run | Serverless compute |
| **Scheduling**       | Cloud Scheduler  | Periodic updates   |
| **Secrets**          | Secret Manager   | Token storage (✅ Integrated) |
| **Logging**          | Cloud Logging    | Centralized logs   |

---

## 📦 Project Structure

```
Grace-Irvine-Ministry-Clean/
│
├── api/                         # 🔵 API Service (Data cleaning & REST API)
│   ├── app.py                   # FastAPI application
│   ├── Dockerfile               # API service container
│   └── README.md                # API documentation
│
├── mcp/                         # 🟢 MCP Service (AI assistant integration)
│   ├── mcp_server.py            # Unified MCP server (stdio + HTTP)
│   ├── sse_transport.py         # HTTP/SSE transport handler
│   ├── Dockerfile               # MCP service container
│   └── README.md                # MCP documentation
│
├── core/                        # 🔧 Shared business logic (80%+ reuse)
│   ├── clean_pipeline.py        # Main cleaning orchestration
│   ├── service_layer.py         # Service layer transformer
│   ├── cleaning_rules.py        # Cleaning rules
│   ├── validators.py            # Data validators
│   ├── alias_utils.py           # Alias mapping
│   ├── gsheet_utils.py          # Google Sheets client
│   ├── cloud_storage_utils.py   # Cloud Storage client
│   ├── change_detector.py       # Change detection
│   └── schema_manager.py        # Schema management
│
├── deploy/                      # 📦 Deployment scripts
│   ├── deploy-api.sh            # Deploy API service
│   ├── deploy-mcp.sh            # Deploy MCP service
│   └── deploy-all.sh            # Deploy all services
│
├── config/                      # ⚙️ Configuration files
│   ├── config.json              # Main configuration
│   ├── claude_desktop_config.example.json   # Claude Desktop config
│   ├── env.example              # Environment variables
│   └── service-account.json     # GCP service account
│
├── docs/                        # 📚 Documentation
│   ├── ARCHITECTURE.md          # System architecture
│   ├── API_ENDPOINTS.md         # API reference
│   ├── MCP_DESIGN.md            # MCP architecture
│   ├── MCP_DEPLOYMENT.md        # MCP cloud deployment
│   ├── SERVICE_LAYER.md         # Service layer design
│   ├── DEPLOYMENT.md            # Cloud deployment
│   └── TROUBLESHOOTING.md       # Common issues
│
├── tests/                       # 🧪 Tests
│   ├── test_cleaning.py         # Unit tests
│   ├── sample_raw.csv           # Sample raw data
│   └── sample_aliases.csv       # Sample aliases
│
├── logs/                        # 📊 Logs and outputs
│   ├── clean_preview.csv        # Cleaned data (CSV)
│   ├── clean_preview.json       # Cleaned data (JSON)
│   ├── service_layer/           # Service layer data
│   └── validation_report_*.txt  # Validation reports
│
├── CHANGELOG.md                 # Version history
├── README.md                    # This file
├── requirements.txt             # Python dependencies
└── .gitignore                   # Git ignore rules
```

---

## 💡 Usage Examples

### Example 1: AI Query via Claude Desktop

**User**: "Show me next Sunday's service schedule"

**Claude** (using MCP tools):

```
Using query_volunteers_by_date tool with date=2025-10-26...

Next Sunday (2025-10-26) Service Schedule:

📖 Sermon: "The Power of Prayer" by Pastor Zhang
   Series: Prayer Series | Scripture: Matthew 6:9-13

🎵 Worship Team:
   - Lead: Wang Li
   - Team: Chen Ming, Lin Fang
   - Pianist: Li Wei

🎤 Technical Team:
   - Audio: Zhao Qiang
   - Video: Zhou Chen
```

---

### Example 2: REST API Query

```bash
# Get sermon records for 2024
curl "https://your-api.run.app/api/v1/sermon?year=2024"

# Get volunteer assignments for a specific date
curl "https://your-api.run.app/api/v1/volunteer/by-person/person_wangli"

# Trigger data cleaning (requires Bearer token)
curl -X POST "https://your-api.run.app/api/v1/clean" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}'
```

---

### Example 3: Local Cleaning Pipeline

```bash
# Test with dry-run mode
python core/clean_pipeline.py --config config/config.json --dry-run

# Output:
# ✅ Read source data: 100 rows
# ✅ Cleaned successfully: 95 rows
# ⚠️  Warnings: 3 rows
# ❌ Errors: 2 rows
# ✅ Generated logs/clean_preview.json

# Run actual cleaning
python core/clean_pipeline.py --config config/config.json
```

---

## 🧪 Testing

### Run Unit Tests

```bash
# Run all tests
pytest tests/test_cleaning.py -v

# Run specific test class
pytest tests/test_cleaning.py::TestCleaningRules -v

# Run specific test method
pytest tests/test_cleaning.py::TestCleaningRules::test_clean_date_formats -v
```

### Test Coverage

Unit tests cover:

- ✅ Date format cleaning and normalization
- ✅ Text cleaning (spaces, placeholders)
- ✅ Scripture reference formatting
- ✅ Song splitting and deduplication
- ✅ Column merging
- ✅ Alias mapping
- ✅ Data validation (required fields, date validity, duplicate detection)

### Sample Data

`tests/sample_raw.csv` includes various test scenarios:

- Different date formats
- Text with spaces
- Multiple song delimiters
- Alias names
- Null values and placeholders
- Invalid dates (for error handling tests)

---

## 🔒 Security & Permissions

### Minimum Privilege Principle

- ✅ Source sheets: Read-only (Viewer) permission
- ✅ Target sheets: Write-only to specific ranges
- ✅ Alias sheets: Read-only (Viewer) permission

### Sensitive Information Protection

- ❌ **DO NOT** commit service account JSON files to repository
- ✅ Use `.gitignore` to exclude `*.json` (except `config/config.json`)
- ✅ Use environment variable `GOOGLE_APPLICATION_CREDENTIALS`
- ✅ **Secret Manager Integration**: All services automatically read tokens from Google Secret Manager
- ✅ **Automatic Fallback**: Services read from Secret Manager first, then environment variables
- ✅ Store tokens in Secret Manager for production (recommended)
- ✅ Use environment variables for local development
- ❌ Never print sensitive tokens in logs

**Secret Manager Support**:
- All 3 Cloud Run services integrate with Secret Manager
- 4 secrets managed: `mcp-bearer-token`, `api-scheduler-token`, `weekly-preview-scheduler-token`, `weekly-preview-smtp-password`
- Automatic token rotation support
- See [Secret Management Guide](docs/SECRET_MANAGEMENT.md) and [Secrets Inventory](docs/SECRETS_INVENTORY.md)

### Authentication

**API Service**:

- Bearer Token authentication for protected endpoints
- Public access for health checks and documentation
- Configurable via environment variable

**MCP Service**:

- Bearer Token authentication for HTTP/SSE mode (optional)
- No authentication for stdio mode (local only)
- CORS middleware enabled for remote clients
- Bearer Token automatically loaded from Secret Manager (`mcp-bearer-token`)

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Report Issues**: Found a bug? [Open an issue](https://github.com/yourusername/Grace-Irvine-Ministry-Clean/issues)
2. **Suggest Features**: Have an idea? Share it in discussions
3. **Submit PRs**: Fork, create a feature branch, and submit a pull request
4. **Improve Docs**: Help us make documentation clearer

### Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/Grace-Irvine-Ministry-Clean.git
cd Grace-Irvine-Ministry-Clean

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Start API service locally
cd api && uvicorn app:app --reload

# Start MCP service locally
cd mcp && python mcp_server.py
```

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **FastAPI** - Modern Python web framework
- **MCP SDK** - Model Context Protocol implementation
- **Google Cloud** - Cloud infrastructure
- **Anthropic Claude** - AI assistant integration

---

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/Grace-Irvine-Ministry-Clean/issues)
- **Email**: jonathanjing@graceirvine.org

---

**Built with ❤️ for Grace Irvine Church Ministry**
