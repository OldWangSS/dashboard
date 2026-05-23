#!/usr/bin/env python3
"""Build status.json from cloud Windows data sources and push to GitHub Pages.

Sources on cloud Windows (192.168.1.5):
  - D:/Projects/dashboard/content/news/daily_briefing.json
  - D:/Projects/dashboard/content/football/prediction.json
  - D:/Projects/dashboard/content/football/replay.json

Output: dashboard/data/status.json -> git commit -> git push
"""
import json, os, subprocess, re, sys
from datetime import datetime

REPO = "/root/dashboard"
SSH_KEY = os.path.expanduser("~/.ssh/id_ed25519_cloudwin")
SSH_HOST = "Administrator@192.168.1.5"

def scp_get(remote_path, local_path):
    """Pull a file from cloud Windows via SCP"""
    cmd = [
        "scp", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        f"{SSH_HOST}:{remote_path}", local_path
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return r.returncode == 0
    except:
        return False

def load_json_any(path):
    """Load JSON with multi-encoding fallback"""
    if not os.path.exists(path):
        return None
    with open(path, 'rb') as f:
        raw = f.read()
    for enc in ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'cp936']:
        try:
            return json.loads(raw.decode(enc))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    return None

def main():
    tmp = "/tmp/dashboard_sync"
    os.makedirs(tmp, exist_ok=True)

    # Pull sources
    news_ok = scp_get(
        "D:/Projects/dashboard/content/news/daily_briefing.json",
        f"{tmp}/daily_briefing.json"
    )
    pred_ok = scp_get(
        "D:/Projects/dashboard/content/football/prediction.json",
        f"{tmp}/prediction.json"
    )
    replay_ok = scp_get(
        "D:/Projects/dashboard/content/football/replay.json",
        f"{tmp}/replay.json"
    )
    print(f"Pull: news={news_ok} pred={pred_ok} replay={replay_ok}")

    # Load data
    news = load_json_any(f"{tmp}/daily_briefing.json")
    pred = load_json_any(f"{tmp}/prediction.json")
    replay = load_json_any(f"{tmp}/replay.json")

    # Load existing status.json
    status_path = os.path.join(REPO, "dashboard", "data", "status.json")
    data = {}
    if os.path.exists(status_path):
        try:
            with open(status_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            pass

    # Populate news
    if news:
        data["news"] = {"source": news.get("source",""), "items": news.get("items",[])}
        data["ai_news"] = {"source": news.get("source",""), "updated": news.get("updated",""), "items": news.get("items",[])}

    # Populate football
    if pred:
        football = {"predictions": pred.get("predictions",[]), "date": pred.get("date","")}
        if replay:
            content = replay.get("content","")
            hit_m = re.search(r'精确命中[：:]\s*(\d+)', content)
            dir_m = re.search(r'方向命中[：:]\s*(\d+)', content)
            total_m = re.search(r'(\d+)\s*场预测', content)
            football["review"] = {
                "hit": int(hit_m.group(1)) if hit_m else 0,
                "direction": int(dir_m.group(1)) if dir_m else 0,
                "total": int(total_m.group(1)) if total_m else len(football["predictions"]),
            }
        data["football"] = football

    # System status (all online unless known otherwise)
    data["system"] = {"abyss": True, "catclaw": True, "hermes": True, "hmcode": True, "homebot": True}

    # Token placeholder
    if "token" not in data:
        data["token"] = {"today": 0, "month": 0, "today_tokens": 0, "month_tokens": 0}

    data["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Write
    os.makedirs(os.path.dirname(status_path), exist_ok=True)
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"status.json: {len(json.dumps(data))} bytes")

    # Git commit + push
    os.chdir(REPO)
    subprocess.run(["git", "add", "dashboard/data/status.json"], check=True)
    r = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if r.returncode == 0:
        print("No changes")
    else:
        ts = datetime.now().strftime("%m-%d %H:%M")
        subprocess.run(["git", "commit", "-m", f"sync dashboard {ts}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print(f"Pushed {ts}")

if __name__ == "__main__":
    main()
