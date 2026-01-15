#!/usr/bin/env python3
"""
Local weekly preview test without MCP.
Loads data from logs/service_layer and calls generate_weekly_preview directly.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
LOGS_DIR = PROJECT_ROOT / "logs" / "service_layer"
CONFIG_PATH = PROJECT_ROOT / "config" / "config.json"


def get_next_sunday() -> str:
    today = datetime.now()
    days_until_sunday = (6 - today.weekday()) % 7
    if days_until_sunday == 0:
        days_until_sunday = 7
    next_sunday = today + timedelta(days=days_until_sunday)
    return next_sunday.strftime("%Y-%m-%d")


def _get_expected_files(year: str | None) -> list[Path]:
    if year:
        return [
            LOGS_DIR / year / f"sermon_{year}.json",
            LOGS_DIR / year / f"volunteer_{year}.json",
        ]
    return [
        LOGS_DIR / "sermon.json",
        LOGS_DIR / "volunteer.json",
    ]


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_role_display_name(role: str, config: dict) -> str:
    columns_mapping = config.get("columns", {})
    if role in columns_mapping:
        display = columns_mapping[role]
        if isinstance(display, dict):
            sources = display.get("sources", [])
            display = sources[0] if sources else role
        if isinstance(display, str):
            return display.rstrip("0123456789")
    return role


def load_service_layer(domain: str, year: str | None) -> dict:
    if year:
        data_path = LOGS_DIR / year / f"{domain}_{year}.json"
    else:
        data_path = LOGS_DIR / f"{domain}.json"
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_sermon_record(record: dict, config: dict) -> str:
    lines = [f"📅 服侍日期: {record.get('service_date', 'N/A')}"]
    preacher = record.get("preacher", {})
    if preacher.get("name"):
        lines.append(f"  🎤 {get_role_display_name('preacher', config)}: {preacher['name']}")
    reading = record.get("reading", {})
    if reading.get("name"):
        lines.append(f"  📖 {get_role_display_name('reading', config)}: {reading['name']}")
    sermon = record.get("sermon", {})
    if sermon.get("series"):
        lines.append(f"  📚 系列: {sermon['series']}")
    if sermon.get("title"):
        lines.append(f"  📖 标题: {sermon['title']}")
    if sermon.get("scripture"):
        lines.append(f"  📜 经文: {sermon['scripture']}")
    songs = record.get("songs", [])
    if songs:
        lines.append(f"  🎵 诗歌: {', '.join(songs)}")
    return "\n".join(lines)


def format_volunteer_record(record: dict, config: dict) -> str:
    lines = [f"📅 服侍日期: {record.get('service_date', 'N/A')}"]
    departments = config.get("departments", {})
    
    def get_name(person):
        if not person:
            return ""
        if isinstance(person, dict):
            return person.get("name", "")
        return ""

    worship = record.get("worship", {})
    if worship:
        dept_name = departments.get("worship", {}).get("name", "敬拜团队")
        lines.append(f"\n🎵 {dept_name}:")
        lead_name = get_name(worship.get("lead"))
        if lead_name:
            lines.append(f"  • {get_role_display_name('worship_lead', config)}: {lead_name}")
        team_names = [m.get("name") for m in worship.get("team", []) if isinstance(m, dict) and m.get("name")]
        if team_names:
            lines.append(f"  • {get_role_display_name('worship_team', config)}: {', '.join(team_names)}")
        pianist_name = get_name(worship.get("pianist"))
        if pianist_name:
            lines.append(f"  • {get_role_display_name('pianist', config)}: {pianist_name}")

    technical = record.get("technical", {})
    if technical:
        dept_name = departments.get("technical", {}).get("name", "技术团队")
        tech_lines = []
        for role in ["audio", "video", "propresenter_play", "propresenter_update", "video_editor"]:
            person_name = get_name(technical.get(role))
            if person_name:
                tech_lines.append(f"  • {get_role_display_name(role, config)}: {person_name}")
        if tech_lines:
            lines.append(f"\n🔧 {dept_name}:")
            lines.extend(tech_lines)

    education = record.get("education", {})
    if education:
        dept_name = departments.get("education", {}).get("name", "儿童部")
        edu_lines = []
        friday_name = get_name(education.get("friday_child_ministry"))
        if friday_name:
            edu_lines.append(f"  • {get_role_display_name('friday_child_ministry', config)}: {friday_name}")
        assistants = education.get("sunday_child_assistants", [])
        names = [a.get("name") for a in assistants if isinstance(a, dict) and a.get("name")]
        if names:
            edu_lines.append(f"  • {get_role_display_name('sunday_child_assistant', config)}: {', '.join(names)}")
        if edu_lines:
            lines.append(f"\n👶 {dept_name}:")
            lines.extend(edu_lines)

    outreach = record.get("outreach", {})
    if outreach:
        dept_name = departments.get("outreach", {}).get("name", "外展联络")
        out_lines = []
        for role in ["newcomer_reception_1", "newcomer_reception_2"]:
            person_name = get_name(outreach.get(role))
            if person_name:
                out_lines.append(f"  • {get_role_display_name(role, config)}: {person_name}")
        if out_lines:
            lines.append(f"\n🤝 {dept_name}:")
            lines.extend(out_lines)

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Local weekly preview test")
    parser.add_argument("--date", type=str, help="YYYY-MM-DD, default next Sunday")
    parser.add_argument("--format", type=str, default="text", choices=["text", "markdown", "html"])
    parser.add_argument("--year", type=str, help="Optional year for service_layer data")
    args = parser.parse_args()

    date_str = args.date or get_next_sunday()

    expected_files = _get_expected_files(args.year)
    missing_files = [p for p in expected_files if not p.exists()]
    if missing_files:
        print("本地服务层数据不存在，无法生成预览。", file=sys.stderr)
        for path in missing_files:
            print(f"缺少文件: {path}", file=sys.stderr)
        print("请先运行清洗管线生成 logs/service_layer 数据。", file=sys.stderr)
        return 1

    config = load_config()
    sermons = load_service_layer("sermon", args.year).get("sermons", [])
    volunteers = load_service_layer("volunteer", args.year).get("volunteers", [])

    day_sermons = [s for s in sermons if s.get("service_date", "").startswith(date_str)]
    day_volunteers = [v for v in volunteers if v.get("service_date", "").startswith(date_str)]

    sermon = day_sermons[0] if day_sermons else {}
    volunteer = day_volunteers[0] if day_volunteers else {}

    if args.format == "markdown":
        lines = [f"### 主日预览 {date_str}\n", "#### 📖 证道信息"]
        if sermon:
            lines.append(format_sermon_record(sermon, config))
        else:
            lines.append("待定")
        lines.append("\n#### 👥 同工安排")
        if volunteer:
            lines.append(format_volunteer_record(volunteer, config))
        else:
            lines.append("待定")
        print("\n".join(lines))
    elif args.format == "html":
        html = [f"<h3>主日预览 {date_str}</h3>"]
        html.append("<h4>📖 证道信息</h4>")
        html.append(f"<pre>{format_sermon_record(sermon, config)}</pre>" if sermon else "<p>待定</p>")
        html.append("<h4>👥 同工安排</h4>")
        html.append(f"<pre>{format_volunteer_record(volunteer, config)}</pre>" if volunteer else "<p>待定</p>")
        print("".join(html))
    else:
        lines = [f"=== 主日预览 {date_str} ==="]
        lines.append("\n📖 证道信息:")
        lines.append(format_sermon_record(sermon, config) if sermon else "待定")
        lines.append("\n👥 同工安排:")
        lines.append(format_volunteer_record(volunteer, config) if volunteer else "待定")
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

