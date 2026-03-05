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
        "good_elements": [],
        "bad_patterns": [],
        "stats": {"total_generated": 0, "good_count": 0, "bad_count": 0},
    }


def _save_history(data: dict):
    _ensure_dirs()
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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


def get_good_elements() -> list:
    """過去に好評だった要素リスト"""
    return _load_history().get("good_elements", [])


def get_bad_patterns() -> list:
    """過去に悪評だったパターンリスト"""
    return _load_history().get("bad_patterns", [])


def get_reference_scripts(script_type: str, n: int = 2) -> list:
    """goodフォルダから同タイプの台本をn件取得（参考用）"""
    _ensure_dirs()
    files = sorted(
        GOOD_DIR.glob(f"{script_type}_*.txt"),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    results = []
    for f in files[:n]:
        with open(f, encoding="utf-8") as fp:
            results.append(fp.read())
    return results


def save_script(script: str, rating: str, theme: str, script_type: str, angle: str):
    """台本を good/ or bad/ に保存"""
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

    # 統計を更新
    history = _load_history()
    stats = history.setdefault("stats", {})
    if rating == "good":
        stats["good_count"] = stats.get("good_count", 0) + 1
    else:
        stats["bad_count"] = stats.get("bad_count", 0) + 1
    _save_history(history)


def record_theme_used(theme: str, script_type: str, angle: str):
    """テーマ使用済みを記録し、次のアングルに進める"""
    history = _load_history()

    history.setdefault("used_themes", []).append({
        "theme": theme,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "type": script_type,
        "angle": angle,
    })
    # 最新50件だけ保持
    history["used_themes"] = history["used_themes"][-50:]

    # 統計更新
    stats = history.setdefault("stats", {})
    stats["total_generated"] = stats.get("total_generated", 0) + 1

    # アングルを次に進める
    idx = history.get("next_angle_index", 0)
    history["next_angle_index"] = (idx + 1) % len(ANGLE_ROTATION)

    _save_history(history)


def get_stats() -> dict:
    return _load_history().get("stats", {})
