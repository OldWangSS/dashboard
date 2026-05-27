#!/usr/bin/env python3
"""gen_data.py — 网站数据聚合器 v2
独立脚本，无 Agent 工具依赖。每个数据源独立 try-except + 缺省值兜底。
"""
import json, os, subprocess, re
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
REPO = "/root/dashboard"
STATUS_PATH = f"{REPO}/dashboard/data/status.json"
SESSIONS_DIR = os.path.expanduser("~/.hermes/sessions")
PROFILE_SESSIONS = [
    os.path.expanduser("~/.hermes/profiles/yuheng/sessions"),
    os.path.expanduser("~/.hermes/profiles/kaiyang/sessions"),
]
OBSIDIAN = os.path.expanduser("~/Obsidian")  # 若有则 git log

def safe(default):
    """装饰器：异常时返回 default"""
    def deco(fn):
        def wrapper(*a, **kw):
            try:
                return fn(*a, **kw)
            except Exception:
                return default
        return wrapper
    return deco

# ═══════════════════════════════════════════
# 数据源1: 系统状态（端口探测）
# ═══════════════════════════════════════════
@safe({})
def fetch_system():
    import socket
    agents = {
        "tianshu":   ("天枢·贪狼", 18801, "127.0.0.1"),
        "yuheng":    ("玉衡·廉贞", 18807, "192.168.1.5"),
        "kaiyang":   ("开阳·武曲", 18806, "192.168.1.5"),
        "tianji":    ("天玑·禄存", 18805, "192.168.1.5"),
        "tianquan":  ("天权·文曲", 18790, "192.168.1.5"),
        "tianxuan":  ("天璇·巨门", 18804, "192.168.1.5"),
        "yaoguang":  ("瑶光·破军", 18789, "192.168.1.5"),
    }
    result = {}
    for aid, (name, port, host) in agents.items():
        try:
            s = socket.create_connection((host, port), timeout=3)
            s.close()
            result[aid] = {"name": name, "status": True}
        except:
            result[aid] = {"name": name, "status": False}
    return result

# ═══════════════════════════════════════════
# 数据源2: Token 统计
# ═══════════════════════════════════════════
@safe({"today_tokens": 0, "note": "无数据"})
def fetch_token():
    today = datetime.now(CST).strftime("%Y-%m-%d")
    total = 0
    for d in [SESSIONS_DIR] + PROFILE_SESSIONS:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if not f.endswith(".jsonl") or today not in f:
                continue
            try:
                with open(os.path.join(d, f)) as fh:
                    for line in fh:
                        try:
                            rec = json.loads(line)
                            if isinstance(rec, dict):
                                total += rec.get("usage", {}).get("total_tokens", 0) or 0
                        except:
                            pass
            except:
                pass
    return {"today_tokens": total, "note": "auto" if total > 0 else "无session数据"}

# ═══════════════════════════════════════════
# 数据源3: 每日新闻（从 session 历史提取）
# ═══════════════════════════════════════════
@safe({"source": "无数据", "items": []})
def fetch_news():
    # 找最近的 session 里包含"每日早报"或"news"的输出
    items = []
    for d in [SESSIONS_DIR] + PROFILE_SESSIONS:
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d), reverse=True)[:20]:
            if not f.endswith(".jsonl"):
                continue
            try:
                with open(os.path.join(d, f)) as fh:
                    for line in fh:
                        try:
                            rec = json.loads(line)
                            content = str(rec.get("content", ""))
                            if "每日早报" in content or "AI 行业前沿" in content:
                                items.append(content[:200])
                        except:
                            pass
            except:
                pass
            if len(items) >= 5:
                break
        if items:
            break
    return {"source": "session", "updated": datetime.now(CST).isoformat(), "items": items[:5]}

# ═══════════════════════════════════════════
# 数据源4: 知识库更新
# ═══════════════════════════════════════════
@safe({"updated": "无Obsidian", "recent": []})
def fetch_knowledge():
    if not os.path.isdir(OBSIDIAN):
        return {"updated": "Obsidian目录不存在", "recent": []}
    try:
        r = subprocess.run(["git", "-C", OBSIDIAN, "log", "--since=7 days ago", "--oneline", "--", "*.md"],
                          capture_output=True, text=True, timeout=15)
        lines = [l for l in r.stdout.strip().split("\n") if l][:10]
        return {"updated": datetime.now(CST).strftime("%Y-%m-%d"), "recent": lines}
    except:
        return {"updated": "git失败", "recent": []}

# ═══════════════════════════════════════════
# 数据源5: 运行日报
# ═══════════════════════════════════════════
@safe({"tasks": [], "agents_called": 0, "note": "无数据"})
def fetch_daily():
    today = datetime.now(CST).strftime("%Y-%m-%d")
    tasks = set()
    agent_calls = 0
    for d in [SESSIONS_DIR] + PROFILE_SESSIONS:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if not f.endswith(".jsonl") or today not in f:
                continue
            agent_calls += 1
            try:
                with open(os.path.join(d, f)) as fh:
                    for line in fh:
                        try:
                            rec = json.loads(line)
                            content = str(rec.get("content", ""))
                            if len(content) > 50:
                                tasks.add(content[:120])
                        except:
                            pass
            except:
                pass
    return {"tasks": list(tasks)[:8], "agents_called": agent_calls}

# ═══════════════════════════════════════════
# 数据源6: 足球预测
# ═══════════════════════════════════════════
@safe({"predictions": [], "note": "无数据"})
def fetch_football():
    # 从 dashboard data 目录读预抓数据
    fp = os.path.join(REPO, "data", "football_pred.json")
    if os.path.exists(fp):
        with open(fp, encoding="utf-8") as f:
            return json.load(f)
    return {"predictions": [], "note": "football_pred.json缺失"}

@safe({"status": "disabled", "note": "无法获取"})
def fetch_curator():
    """数据源7: Curator 技能管家状态"""
    try:
        r = subprocess.run(
            ["hermes", "curator", "status"],
            capture_output=True, text=True, timeout=30
        )
        if r.returncode != 0:
            return {"status": "error", "note": r.stderr[:200]}
        
        output = r.stdout
        result = {"status": "enabled"}
        
        if "ENABLED" in output:
            result["enabled"] = True
        else:
            result["enabled"] = False
        
        m = re.search(r"runs:\s+(\d+)", output)
        if m: result["total_runs"] = int(m.group(1))
        
        m = re.search(r"last run:\s+(.+)", output)
        if m: result["last_run"] = m.group(1).strip()
        
        m = re.search(r"interval:\s+(.+)", output)
        if m: result["interval"] = m.group(1).strip()
        
        m = re.search(r"agent-created skills:\s+(\d+)\s+total", output)
        if m: result["skills_total"] = int(m.group(1))
        
        m = re.search(r"active\s+(\d+)", output)
        if m: result["skills_active"] = int(m.group(1))
        
        m = re.search(r"stale\s+(\d+)", output)
        if m: result["skills_stale"] = int(m.group(1))
        
        # Most active skills
        most_active = []
        in_most = False
        for line in output.split('\n'):
            if 'most active' in line.lower():
                in_most = True
                continue
            if in_most:
                if 'least' in line.lower() or not line.strip():
                    break
                if 'activity=' in line:
                    parts = line.strip().split()
                    if parts:
                        most_active.append(parts[0])
        result["most_active_skills"] = most_active[:3]
        
        m = re.search(r"last summary:\s+(auto:.+)", output)
        if m: result["last_summary"] = m.group(1).strip()[:300]
        
        result["updated"] = datetime.now(CST).strftime("%Y-%m-%d %H:%M")
        return result
    except Exception as e:
        return {"status": "error", "note": str(e)[:200]}


# ═══════════════════════════════════════════
# 聚合
# ═══════════════════════════════════════════
def main():
    data = {}
    if os.path.exists(STATUS_PATH):
        with open(STATUS_PATH, encoding="utf-8") as f:
            data = json.load(f)

    data["system"] = fetch_system()
    data["token"] = fetch_token()
    data["news"] = fetch_news()
    data["knowledge"] = fetch_knowledge()
    data["daily"] = fetch_daily()
    data["football"] = fetch_football()
    data["curator"] = fetch_curator()
    data["updated"] = datetime.now(CST).strftime("%Y-%m-%d %H:%M")

    os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)
    with open(STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Git push
    os.chdir(REPO)
    subprocess.run(["git", "add", "dashboard/data/status.json"], check=True)
    r = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if r.returncode != 0:
        ts = datetime.now(CST).strftime("%m-%d %H:%M")
        subprocess.run(["git", "commit", "-m", f"sync dashboard {ts}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print(f"✅ {ts} pushed")
    else:
        print("no changes")

if __name__ == "__main__":
    main()
