#!/usr/bin/env python3
"""仪表盘内容更新 — 由每日早报/足球 cron 调用，把产出灌入 status.json

支持两种调用方式：
  1. stdin 管道:  echo '{"news": {...}}' | python dashboard_content_updater.py
  2. --json 参数: python dashboard_content_updater.py --json '{"news": {...}}'
"""
import json, sys, os, argparse
from datetime import datetime

def _data_file():
    """根据操作系统自动选择路径"""
    if sys.platform == "win32":
        return r"F:\AgentDownload\dashboard\data\status.json"
    else:
        return "/mnt/f/AgentDownload/dashboard/data/status.json"

DATA_FILE = _data_file()

def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", dest="json_str", help="JSON string to merge")
    args = parser.parse_args()

    # 读取输入：优先 --json 参数，否则 stdin
    if args.json_str:
        raw = args.json_str
    else:
        if sys.stdin.isatty():
            print("ERROR: no --json arg and no stdin pipe", file=sys.stderr)
            print("Usage: echo '{\"news\":{...}}' | python dashboard_content_updater.py", file=sys.stderr)
            print("   or: python dashboard_content_updater.py --json '{\"news\":{...}}'", file=sys.stderr)
            sys.exit(1)
        raw = sys.stdin.read()

    try:
        incoming = json.loads(raw)
    except Exception as e:
        print(f"ERROR: invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    data = load()

    # 合并每个顶层字段
    for key in ("daily", "news", "ai_news", "football", "weekly"):
        if key in incoming and incoming[key] is not None:
            data[key] = incoming[key]

    data["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save(data)
    print(f"OK: updated {list(incoming.keys())} → {DATA_FILE}")

if __name__ == "__main__":
    main()
