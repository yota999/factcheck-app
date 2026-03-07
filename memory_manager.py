import os
import json
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path(__file__).parent / "memory"
GOOD_DIR = MEMORY_DIR / "good"
BAD_DIR = MEMORY_DIR / "bad"
HISTORY_FILE = MEMORY_DIR / "history.json"

# アングルは科学・感情・体験談・論破・行動の5種類でローテーション
ANGLE_ROTATION = ["science", "emotion", "story", "debate", "action"]
ANGLE_NAMES = {
    "science": "科学・データ根拠型",
    "emotion": "感情・共感型",
    "story": "体験談・ストーリー型",
    "debate": "常識論破・逆説型",
    "action": "今すぐ行動型",
}

# 使用するAIモデルのローテーション
AI_ROTATION = [
    ("anthropic/claude-sonnet-4-6", "Claude Sonnet 4.6"),
    ("openai/gpt-4o", "GPT-4o"),
    ("gemini/gemini-1.5-pro", "Gemini 1.5 Pro"),
    ("xai/grok-2", "Grok 2"),
]


def _ensure_dirs():
    GOOD_DIR.mkdir(parents=True, exist_ok=True)
    BAD_DIR.mkdir(parents=True, exist_ok=True)


def _load_history() -> dict:
    _ensure_dirs()
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "used_themes": [],
        "next_angle_index": 0,
        "next_ai_index": 0,
        "good_elements": [],
        "bad_patterns": [],
        "rejected_themes": [],
        "rejected_ideas": [],
        "stats": {"total_generated": 0, "good_count": 0, "bad_count": 0},
    }


def _save_history(data: dict):
    _ensure_dirs()
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _ensure_keys(history: dict) -> dict:
    """古いhistory.jsonに新しいキーがない場合に補完する"""
    defaults = {
        "next_ai_index": 0,
        "rejected_themes": [],
        "rejected_ideas": [],
        "good_elements": history.get("good_elements", []),
        "bad_patterns": history.get("bad_patterns", []),
    }
    for k, v in defaults.items():
        history.setdefault(k, v)
    return history


# ── 読み取り系 ────────────────────────────────────────────────────────

def get_used_themes() -> list:
    """過去に使ったテーマ一覧（重複防止用）"""
    history = _load_history()
    return [t["theme"] for t in history.get("used_themes", [])]


def get_next_angle() -> tuple:
    """次に使うアングルを返す (angle_key, angle_name)"""
    history = _load_history()
    idx = history.get("next_angle_index", 0) % len(ANGLE_ROTATION)
    angle = ANGLE_ROTATION[idx]
    return angle, ANGLE_NAMES[angle]


def get_next_ai() -> tuple:
    """次に使うAIモデルを返す (model_id, model_name)"""
    history = _ensure_keys(_load_history())
    idx = history.get("next_ai_index", 0) % len(AI_ROTATION)
    return AI_ROTATION[idx]


def get_good_elements() -> list:
    return _load_history().get("good_elements", [])


def get_bad_patterns() -> list:
    return _load_history().get("bad_patterns", [])


def get_rejected_themes() -> list:
    """NG登録されたテーマ一覧"""
    return _ensure_keys(_load_history()).get("rejected_themes", [])


def get_rejected_ideas() -> list:
    """NG登録されたアイデア一覧"""
    return _ensure_keys(_load_history()).get("rejected_ideas", [])


def get_reference_scripts(script_type: str, n: int = 3) -> list:
    """goodフォルダから同タイプの台本をランダムn件取得（参考用・毎回違うものが選ばれる）"""
    import random
    _ensure_dirs()
    files = list(GOOD_DIR.glob(f"{script_type}_*.txt"))
    # 内容が空でないファイルだけ対象にする
    valid = []
    for f in files:
        try:
            content = f.read_text(encoding="utf-8")
            body = "\n".join(
                l for l in content.split("\n")
                if not l.startswith("#") and l.strip()
            )
            if len(body) > 100:
                valid.append((f, body))
        except Exception:
            pass
    # ランダムにn件選ぶ
    chosen = random.sample(valid, min(n, len(valid)))
    return [body for _, body in chosen]


def get_stats() -> dict:
    return _load_history().get("stats", {})


# ── 書き込み系 ────────────────────────────────────────────────────────

def add_rejected_themes(themes: list):
    """テーマをNG登録する（重複なし・最新100件保持）"""
    if not themes:
        return
    history = _ensure_keys(_load_history())
    existing = set(history["rejected_themes"])
    for t in themes:
        if t not in existing:
            history["rejected_themes"].append(t)
            existing.add(t)
    history["rejected_themes"] = history["rejected_themes"][-100:]
    _save_history(history)


def add_rejected_ideas(ideas: list):
    """アイデアをNG登録する（重複なし・最新100件保持）"""
    if not ideas:
        return
    history = _ensure_keys(_load_history())
    existing = set(history["rejected_ideas"])
    for i in ideas:
        if i not in existing:
            history["rejected_ideas"].append(i)
            existing.add(i)
    history["rejected_ideas"] = history["rejected_ideas"][-100:]
    _save_history(history)


def save_script(script: str, rating: str, theme: str, script_type: str, angle: str):
    """台本を good/ or bad/ に保存し、good_elements / bad_patterns を更新する"""
    _ensure_dirs()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{script_type}_{ts}.txt"
    target_dir = GOOD_DIR if rating == "good" else BAD_DIR
    with open(target_dir / filename, "w", encoding="utf-8") as f:
        f.write(f"# テーマ: {theme}\n")
        f.write(f"# タイプ: {script_type}\n")
        f.write(f"# アングル: {angle}\n")
        f.write(f"# 評価: {rating}\n\n")
        f.write(script)

    history = _ensure_keys(_load_history())
    stats = history.setdefault("stats", {})

    if rating == "good":
        stats["good_count"] = stats.get("good_count", 0) + 1
        # 好評台本からテーマ・アングルを good_elements に記録
        element = f"テーマ「{theme}」×アングル「{ANGLE_NAMES.get(angle, angle)}」"
        if element not in history["good_elements"]:
            history["good_elements"].append(element)
        history["good_elements"] = history["good_elements"][-30:]
    else:
        stats["bad_count"] = stats.get("bad_count", 0) + 1
        # 悪評台本のテーマ・アングルを bad_patterns に記録
        pattern = f"テーマ「{theme}」×アングル「{ANGLE_NAMES.get(angle, angle)}」の組み合わせは不評"
        if pattern not in history["bad_patterns"]:
            history["bad_patterns"].append(pattern)
        history["bad_patterns"] = history["bad_patterns"][-30:]

    _save_history(history)


def record_theme_used(theme: str, script_type: str, angle: str):
    """テーマ使用済みを記録し、次のアングル・AIに進める"""
    history = _ensure_keys(_load_history())

    history.setdefault("used_themes", []).append({
        "theme": theme,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "type": script_type,
        "angle": angle,
    })
    history["used_themes"] = history["used_themes"][-50:]

    stats = history.setdefault("stats", {})
    stats["total_generated"] = stats.get("total_generated", 0) + 1

    # アングルを次に進める
    idx = history.get("next_angle_index", 0)
    history["next_angle_index"] = (idx + 1) % len(ANGLE_ROTATION)

    # AIを次に進める
    ai_idx = history.get("next_ai_index", 0)
    history["next_ai_index"] = (ai_idx + 1) % len(AI_ROTATION)

    _save_history(history)


def get_all_scripts_for_history() -> list:
    """生成履歴ページ用：good/bad両方の台本メタデータ一覧を返す"""
    _ensure_dirs()
    scripts = []
    for rating, folder in [("good", GOOD_DIR), ("bad", BAD_DIR)]:
        for f in sorted(folder.glob("*.txt"), key=lambda x: x.stat().st_mtime, reverse=True):
            meta = {"filename": f.name, "rating": rating, "path": str(f),
                    "theme": "", "script_type": "", "angle": "", "date": ""}
            try:
                with open(f, encoding="utf-8") as fp:
                    for line in fp:
                        if line.startswith("# テーマ:"):
                            meta["theme"] = line.replace("# テーマ:", "").strip()
                        elif line.startswith("# タイプ:"):
                            meta["script_type"] = line.replace("# タイプ:", "").strip()
                        elif line.startswith("# アングル:"):
                            meta["angle"] = line.replace("# アングル:", "").strip()
                        elif line.startswith("# 評価:"):
                            pass
                        elif not line.startswith("#") and line.strip():
                            break
            except Exception:
                pass
            # ファイル名から日時を取得
            parts = f.stem.split("_")
            if len(parts) >= 3:
                try:
                    meta["date"] = datetime.strptime(
                        f"{parts[1]}_{parts[2]}", "%Y%m%d_%H%M%S"
                    ).strftime("%Y/%m/%d %H:%M")
                except Exception:
                    meta["date"] = ""
            scripts.append(meta)
    return scripts
