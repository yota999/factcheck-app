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
    ("gemini/gemini-2.5-flash-preview-04-17", "Gemini 2.5 Flash"),
    ("xai/grok-3-mini", "Grok 3 Mini"),
]

SCRIPT_TYPES = ["youtube", "reel"]

# ── Supabase クラウドストレージ ─────────────────────────────────────────
# SUPABASE_URL と SUPABASE_KEY が設定されていればSupabaseを使う
# 未設定ならローカルファイル（history.json）にフォールバック

_supabase_client = None
_supabase_checked = False
SUPABASE_TABLE = "script_memory"  # テーブル名

def _get_supabase():
    """Supabaseクライアントを取得（未設定ならNone）"""
    global _supabase_client, _supabase_checked
    if _supabase_checked:
        return _supabase_client
    _supabase_checked = True
    try:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
        if not url or not key:
            # Streamlit secretsから取得を試みる
            try:
                import streamlit as st
                url = url or st.secrets.get("SUPABASE_URL", "")
                key = key or st.secrets.get("SUPABASE_KEY", "")
            except Exception:
                pass
        if url and key:
            from supabase import create_client
            _supabase_client = create_client(url, key)
    except Exception:
        _supabase_client = None
    return _supabase_client


def _load_from_supabase() -> dict | None:
    """Supabaseからhistoryデータを読み込む（失敗時はNone）"""
    sb = _get_supabase()
    if not sb:
        return None
    try:
        resp = sb.table(SUPABASE_TABLE).select("data").eq("id", "history").execute()
        if resp.data and len(resp.data) > 0:
            return resp.data[0]["data"]
        return {}
    except Exception:
        return None


def _save_to_supabase(data: dict) -> bool:
    """Supabaseにhistoryデータを保存（成功時True）"""
    sb = _get_supabase()
    if not sb:
        return False
    try:
        sb.table(SUPABASE_TABLE).upsert({
            "id": "history",
            "data": data,
            "updated_at": datetime.now().isoformat(),
        }).execute()
        return True
    except Exception:
        return False


# ── ローカルファイル操作 ────────────────────────────────────────────────

def _ensure_dirs():
    GOOD_DIR.mkdir(parents=True, exist_ok=True)
    BAD_DIR.mkdir(parents=True, exist_ok=True)


def _default_type_data() -> dict:
    """台本タイプごとのデフォルトデータ構造"""
    return {
        "used_themes": [],
        "next_angle_index": 0,
        "next_ai_index": 0,
        "good_elements": [],
        "bad_patterns": [],
        "rejected_themes": [],
        "rejected_ideas": [],
        "edit_improvements": [],   # ユーザー編集から学習した改善ルール
        "stats": {"total_generated": 0, "good_count": 0, "bad_count": 0},
    }


def _load_history() -> dict:
    """履歴データを読み込む（Supabase優先、なければローカルファイル）"""
    # 1) Supabaseを試す
    cloud_data = _load_from_supabase()
    if cloud_data is not None:
        data = cloud_data
    else:
        # 2) ローカルファイルにフォールバック
        _ensure_dirs()
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        else:
            data = {}

    # 旧フォーマット（フラット構造）を新フォーマットへ移行
    if data and "youtube" not in data and "reel" not in data:
        data = _migrate_legacy(data)

    # 不足キーを補完
    for t in SCRIPT_TYPES:
        if t not in data:
            data[t] = _default_type_data()
        else:
            for k, v in _default_type_data().items():
                data[t].setdefault(k, v)
    return data


def _migrate_legacy(old: dict) -> dict:
    """旧history.jsonを新フォーマットに変換（既存データを youtube に移行）"""
    new = {}
    for t in SCRIPT_TYPES:
        new[t] = _default_type_data()
    new["youtube"]["used_themes"] = old.get("used_themes", [])
    new["youtube"]["next_angle_index"] = old.get("next_angle_index", 0)
    new["youtube"]["next_ai_index"] = old.get("next_ai_index", 0)
    new["youtube"]["good_elements"] = old.get("good_elements", [])
    new["youtube"]["bad_patterns"] = old.get("bad_patterns", [])
    new["youtube"]["rejected_themes"] = old.get("rejected_themes", [])
    new["youtube"]["rejected_ideas"] = old.get("rejected_ideas", [])
    new["youtube"]["stats"] = old.get("stats", {"total_generated": 0, "good_count": 0, "bad_count": 0})
    return new


def _save_history(data: dict):
    """履歴データを保存（Supabase優先、なければローカルファイル）"""
    # 1) Supabaseに保存を試みる
    if _save_to_supabase(data):
        return
    # 2) ローカルファイルにフォールバック
    _ensure_dirs()
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _type_data(history: dict, script_type: str) -> dict:
    """指定タイプのデータを取得（存在しなければ初期化）"""
    if script_type not in history:
        history[script_type] = _default_type_data()
    return history[script_type]


# ── 読み取り系 ────────────────────────────────────────────────────────

def get_used_themes(script_type: str) -> list:
    """過去に使ったテーマ一覧（タイプ別・重複防止用）"""
    history = _load_history()
    return [t["theme"] for t in _type_data(history, script_type).get("used_themes", [])]


def get_next_angle(script_type: str) -> tuple:
    """次に使うアングルを返す (angle_key, angle_name) タイプ別"""
    history = _load_history()
    idx = _type_data(history, script_type).get("next_angle_index", 0) % len(ANGLE_ROTATION)
    angle = ANGLE_ROTATION[idx]
    return angle, ANGLE_NAMES[angle]


def get_next_ai(script_type: str) -> tuple:
    """次に使うAIモデルを返す (model_id, model_name) タイプ別"""
    history = _load_history()
    idx = _type_data(history, script_type).get("next_ai_index", 0) % len(AI_ROTATION)
    return AI_ROTATION[idx]


def get_good_elements(script_type: str) -> list:
    """好評だった要素一覧（タイプ別）"""
    history = _load_history()
    return _type_data(history, script_type).get("good_elements", [])


def get_bad_patterns(script_type: str) -> list:
    """不評だったパターン一覧（タイプ別）"""
    history = _load_history()
    return _type_data(history, script_type).get("bad_patterns", [])


def get_rejected_themes(script_type: str) -> list:
    """NG登録されたテーマ一覧（タイプ別）"""
    history = _load_history()
    return _type_data(history, script_type).get("rejected_themes", [])


def get_rejected_ideas(script_type: str) -> list:
    """NG登録されたアイデア一覧（タイプ別）"""
    history = _load_history()
    return _type_data(history, script_type).get("rejected_ideas", [])


def get_reference_scripts(script_type: str, n: int = 3) -> list:
    """goodフォルダから同タイプの台本をランダムn件取得（参考用・毎回違うものが選ばれる）"""
    import random
    _ensure_dirs()
    files = list(GOOD_DIR.glob(f"{script_type}_*.txt"))
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
    chosen = random.sample(valid, min(n, len(valid)))
    return [body for _, body in chosen]


def get_stats(script_type: str) -> dict:
    """統計情報（タイプ別）"""
    history = _load_history()
    return _type_data(history, script_type).get("stats", {})


def get_all_stats() -> dict:
    """全タイプの統計合計（サイドバー表示用）"""
    history = _load_history()
    total = {"total_generated": 0, "good_count": 0, "bad_count": 0}
    for t in SCRIPT_TYPES:
        s = _type_data(history, t).get("stats", {})
        for k in total:
            total[k] += s.get(k, 0)
    return total


# ── 書き込み系 ────────────────────────────────────────────────────────

def add_rejected_themes(themes: list, script_type: str):
    """テーマをNG登録する（タイプ別・重複なし・最新100件保持）"""
    if not themes:
        return
    history = _load_history()
    td = _type_data(history, script_type)
    existing = set(td["rejected_themes"])
    for t in themes:
        if t not in existing:
            td["rejected_themes"].append(t)
            existing.add(t)
    td["rejected_themes"] = td["rejected_themes"][-100:]
    _save_history(history)


def get_edit_improvements(script_type: str) -> list:
    """ユーザー編集から学習した改善ルール一覧（タイプ別）"""
    history = _load_history()
    return _type_data(history, script_type).get("edit_improvements", [])


def save_edit_improvements(rules: list, script_type: str):
    """編集改善ルールを保存（タイプ別・最新500件保持）"""
    if not rules:
        return
    history = _load_history()
    td = _type_data(history, script_type)
    existing = td.setdefault("edit_improvements", [])
    for rule in rules:
        if rule not in existing:
            existing.append(rule)
    td["edit_improvements"] = existing[-500:]
    _save_history(history)


def add_rejected_ideas(ideas: list, script_type: str):
    """アイデアをNG登録する（タイプ別・重複なし・最新100件保持）"""
    if not ideas:
        return
    history = _load_history()
    td = _type_data(history, script_type)
    existing = set(td["rejected_ideas"])
    for i in ideas:
        if i not in existing:
            td["rejected_ideas"].append(i)
            existing.add(i)
    td["rejected_ideas"] = td["rejected_ideas"][-100:]
    _save_history(history)


def save_script(script: str, rating: str, theme: str, script_type: str, angle: str):
    """台本を good/ or bad/ に保存し、good_elements / bad_patterns を更新する（タイプ別）"""
    _ensure_dirs()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{script_type}_{ts}.txt"
    target_dir = GOOD_DIR if rating == "good" else BAD_DIR
    try:
        with open(target_dir / filename, "w", encoding="utf-8") as f:
            f.write(f"# テーマ: {theme}\n")
            f.write(f"# タイプ: {script_type}\n")
            f.write(f"# アングル: {angle}\n")
            f.write(f"# 評価: {rating}\n\n")
            f.write(script)
    except Exception:
        pass  # Streamlit Cloudではファイル書き込みが失敗する可能性

    history = _load_history()
    td = _type_data(history, script_type)
    stats = td.setdefault("stats", {})

    if rating == "good":
        stats["good_count"] = stats.get("good_count", 0) + 1
        element = f"テーマ「{theme}」×アングル「{ANGLE_NAMES.get(angle, angle)}」"
        if element not in td["good_elements"]:
            td["good_elements"].append(element)
        td["good_elements"] = td["good_elements"][-30:]
    else:
        stats["bad_count"] = stats.get("bad_count", 0) + 1
        pattern = f"テーマ「{theme}」×アングル「{ANGLE_NAMES.get(angle, angle)}」の組み合わせは不評"
        if pattern not in td["bad_patterns"]:
            td["bad_patterns"].append(pattern)
        td["bad_patterns"] = td["bad_patterns"][-30:]

    _save_history(history)


def record_theme_used(theme: str, script_type: str, angle: str):
    """テーマ使用済みを記録し、次のアングル・AIに進める（タイプ別）"""
    history = _load_history()
    td = _type_data(history, script_type)

    td.setdefault("used_themes", []).append({
        "theme": theme,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "type": script_type,
        "angle": angle,
    })
    td["used_themes"] = td["used_themes"][-50:]

    stats = td.setdefault("stats", {})
    stats["total_generated"] = stats.get("total_generated", 0) + 1

    idx = td.get("next_angle_index", 0)
    td["next_angle_index"] = (idx + 1) % len(ANGLE_ROTATION)

    ai_idx = td.get("next_ai_index", 0)
    td["next_ai_index"] = (ai_idx + 1) % len(AI_ROTATION)

    _save_history(history)


def get_all_scripts_for_history() -> list:
    """生成履歴ページ用：good/bad両方の台本メタデータ一覧を返す"""
    _ensure_dirs()
    scripts = []
    for rating, folder in [("good", GOOD_DIR), ("bad", BAD_DIR)]:
        try:
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
                            elif not line.startswith("#") and line.strip():
                                break
                except Exception:
                    pass
                parts = f.stem.split("_")
                if len(parts) >= 3:
                    try:
                        meta["date"] = datetime.strptime(
                            f"{parts[1]}_{parts[2]}", "%Y%m%d_%H%M%S"
                        ).strftime("%Y/%m/%d %H:%M")
                    except Exception:
                        meta["date"] = ""
                scripts.append(meta)
        except Exception:
            pass
    return scripts
