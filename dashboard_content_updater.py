#!/usr/bin/env python3
"""仪表盘内容更新 — 由每日早报/足球 cron 调用，把产出灌入 status.json

支持两种调用方式：
  1. stdin 管道:  echo '{"news": {...}}' | python dashboard_content_updater.py
  2. --json 参数: python dashboard_content_updater.py --json '{"news": {...}}'
"""
import json, sys, os, argparse
from datetime import datetime

def _data_file():
    """根据操作系统自动选择路径 — 与 dashboard_updater.py 写入同一文件

    优先级：环境变量 DASHBOARD_DATA > 自动检测 > 相对路径
    """
    # 1) 环境变量显式指定
    env_path = os.environ.get("DASHBOARD_DATA", "").strip()
    if env_path:
        return env_path

    # 2) 云 Windows / WSL2 常用路径
    if sys.platform == "win32":
        candidate = r"F:\AgentDownload\dashboard\dashboard\data\status.json"
    else:
        candidate = "/mnt/f/AgentDownload/dashboard/dashboard/data/status.json"

    if os.path.exists(candidate):
        return candidate

    # 3) 回退：相对于脚本所在目录查找 (repo 根下 dashboard/data/status.json)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    fallback = os.path.join(script_dir, "dashboard", "data", "status.json")
    if os.path.exists(fallback):
        return fallback

    # 4) 最后尝试 CWD 相对路径
    return os.path.join("dashboard", "data", "status.json")

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

    if args.json_str:
        raw = args.json_str
    else:
        if sys.stdin.isatty():
            print("ERROR: no --json arg and no stdin pipe", file=sys.stderr)
            sys.exit(1)
        # Windows 上 sys.stdin.read() 默认用 GBK/CP936 解码，中文变问号
        # 必须显式用 UTF-8 读取 raw bytes
        raw = sys.stdin.buffer.read().decode('utf-8')

    try:
        incoming = json.loads(raw)
    except Exception as e:
        print(f"ERROR: invalid JSON input: {e}", file=sys.stderr)
        sys.exit(1)

    data = load()
    for key in ("daily", "news", "ai_news", "football", "weekly"):
        if key in incoming and incoming[key] is not None:
            data[key] = incoming[key]

    data["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save(data)
    print(f"OK: updated {list(incoming.keys())} → {DATA_FILE}")

if __name__ == "__main__":
    main()
