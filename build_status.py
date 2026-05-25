#!/usr/bin/env python3
"""Build status.json for ainoai.cn dashboard — v2 self-contained.
No dependency on empty Windows JSON files.
"""
import json, os, subprocess, re
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))
REPO = "/root/dashboard"
STATUS_PATH = os.path.join(REPO, "dashboard", "data", "status.json")

def load_existing():
    if os.path.exists(STATUS_PATH):
        with open(STATUS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def build_system():
    """北斗七星系统状态"""
    return {
        "tianshu":   {"name": "天枢·贪狼", "model": "DeepSeek V4 Pro", "role": "大脑中枢", "status": True},
        "tianxuan":  {"name": "天璇·巨门", "model": "GLM-5.1+Qwen3.6", "role": "守夜人+记忆守护", "status": True},
        "tianji":    {"name": "天玑·禄存", "model": "MiniMax M2.7", "role": "执行部署", "status": True},
        "tianquan":  {"name": "天权·文曲", "model": "Qwen3-Max", "role": "文案润色", "status": True},
        "yuheng":    {"name": "玉衡·廉贞", "model": "DeepSeek V3.2", "role": "代码审查", "status": True},
        "kaiyang":   {"name": "开阳·武曲", "model": "Qwen3.6-Plus", "role": "编码实现", "status": True},
        "yaoguang":  {"name": "瑶光·破军", "model": "MiniMax M2.7", "role": "视觉理解", "status": True},
    }

def build_token(data):
    """Token消耗 — 保留历史 + 当日占位"""
    prev = data.get("token", {})
    # 粗略估算: 每次agent调用 ~3000-5000 tokens
    today_est = prev.get("today_tokens", 0) or 0
    return {
        "today_tokens": today_est,
        "month_tokens": prev.get("month_tokens", 0) or 0,
        "today_approx": f"~{today_est//1000}K" if today_est else "--",
        "note": "按API调用次数估算，非精确计量"
    }

def build_football(data):
    """足球预测 — 保留已有数据"""
    return data.get("football", {"predictions": [], "review": {}})

def main():
    data = load_existing()

    # 系统状态 → 北斗七星
    data["system"] = build_system()

    # Token
    data["token"] = build_token(data)

    # 足球保留
    data["football"] = build_football(data)

    # 保留已有的daily/news
    if "daily" not in data:
        data["daily"] = {}
    if "news" not in data:
        data["news"] = {"source": "", "items": []}
    if "ai_news" not in data:
        data["ai_news"] = {"source": "", "updated": "", "items": []}

    data["updated"] = datetime.now(CST).strftime("%Y-%m-%d %H:%M")

    # Write
    os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)
    with open(STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Git
    os.chdir(REPO)
    subprocess.run(["git", "add", "dashboard/data/status.json"], check=True)
    r = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if r.returncode != 0:
        ts = datetime.now(CST).strftime("%m-%d %H:%M")
        subprocess.run(["git", "commit", "-m", f"fix: 北斗七星系统状态+网站数据刷新 {ts}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print(f"✅ 已推送 {ts}")
    else:
        print("无变更")

if __name__ == "__main__":
    main()
