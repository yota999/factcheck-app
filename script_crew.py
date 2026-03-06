import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Streamlit Community Cloud の Secrets にも対応
try:
    import streamlit as st
    for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY",
                "XAI_API_KEY", "SERPER_API_KEY"]:
        if key in st.secrets and not os.getenv(key):
            os.environ[key] = st.secrets[key]
except Exception:
    pass


# ── LLM呼び出し（モデルを指定して切り替え可能） ──────────────────────
def _call_llm(prompt: str, model: str = "anthropic/claude-sonnet-4-6",
              temperature: float = 0.7, max_tokens: int = 8000) -> str:
    import litellm
    # xAI の Grok は api_base が必要
    kwargs = dict(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if model.startswith("xai/"):
        kwargs["api_base"] = "https://api.x.ai/v1"
        kwargs["api_key"] = os.getenv("XAI_API_KEY", "")
    response = litellm.completion(**kwargs)
    return response.choices[0].message.content


# ── Serper: 通常検索（最新記事） ────────────────────────────────────
def get_trends(query: str) -> list:
    serper_key = os.getenv("SERPER_API_KEY", "")
    if not serper_key:
        return []
    try:
        import requests
        resp = requests.post(
            "https://google.serper.dev/search",
            json={"q": query, "gl": "jp", "hl": "ja", "num": 5},
            headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
            timeout=10,
        )
        if resp.status_code == 200:
            return [
                f"・{item.get('title', '')}：{item.get('snippet', '')}"
                for item in resp.json().get("organic", [])[:5]
                if item.get("snippet")
            ]
    except Exception:
        pass
    return []


# ── Serper: 動画検索（YouTubeトレンド） ─────────────────────────────
def get_video_trends(query: str) -> list:
    serper_key = os.getenv("SERPER_API_KEY", "")
    if not serper_key:
        return []
    try:
        import requests
        resp = requests.post(
            "https://google.serper.dev/videos",
            json={"q": query, "gl": "jp", "hl": "ja", "num": 5},
            headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
            timeout=10,
        )
        if resp.status_code == 200:
            return [
                f"・{item.get('title', '')}（{item.get('channel', '')}）"
                for item in resp.json().get("videos", [])[:5]
                if item.get("title")
            ]
    except Exception:
        pass
    return []


# ── YouTube Data API v3: 人気動画検索 ───────────────────────────────
def get_youtube_trending(query: str) -> list:
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        return []
    try:
        import requests
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "key": api_key,
                "q": query,
                "part": "snippet",
                "type": "video",
                "regionCode": "JP",
                "relevanceLanguage": "ja",
                "order": "viewCount",
                "maxResults": 5,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return [
                f"・【YouTube人気】{item['snippet']['title']}（{item['snippet']['channelTitle']}）"
                for item in resp.json().get("items", [])
                if item.get("snippet")
            ]
    except Exception:
        pass
    return []


# ── ペルソナ定義 ─────────────────────────────────────────────────────
YOUTUBE_PERSONA = """あなたは、30代〜50代女性から絶大な信頼を得るダイエットトレーナー「町田」として台本を書いてください。
【プロフィール】トレーナー歴14年・指導人数6200人以上・30〜50代女性専門
【口調】優しく寄り添うパートナー口調（デス・マス調）。専門用語は避け、主婦がイメージしやすいたとえ話で説明。
【姿勢】「この人なら信じられる」「今すぐやってみたい」と思わせるレベルで、感情直撃・共感最大化・科学的根拠・即実践可能な解決策をバランスよく入れる。"""

YOUTUBE_STRUCTURE = """【構成（6ブロック厳守）】
1. 【オープニング】視聴者の痛みを直撃する問いかけから始める。最初の30秒で「これは自分のことだ」と思わせる。挨拶とテーマ発表、悩みへの共感。
2. 【実績・事例紹介】ターゲットのリアルな感情と成功体験を具体的に語る
3. 【世間の常識の論破】データや極端なたとえ話を使って徹底的に否定する
4. 【具体的な解決策3つ】科学的テーマで全体を串刺しにして解説、ハードルを下げるフレーズを入れる
5. 【最後の落とし穴】NG行動を念押し、前半の科学的テーマと絡めて伏線回収
6. 【エンディング】まとめ＋熱いメッセージ＋LINE特典誘導＋チャンネル登録のお願い

【文字数】4500〜5000文字（セリフ＝台本本文のみで計算）"""

REEL_PERSONA = """あなたは、解剖学・運動生理学に精通した「35歳以上の女性専門・ボディメイク指導者」として台本を書いてください。
【権威性】「ダイエットのプロとして」「解剖学的に見て」という言葉を使い、曖昧さを排除して断定する。
【厳しさ】努力は認めるが間違った手段には「無駄です」「逆効果です」「一生痩せません」とハッキリ否定する。
【ターゲット】35歳以上の女性。楽な方法に逃げがちだが、本気で体を変えたい主婦・OL・子育て中のママさん。"""

REEL_STRUCTURE = """【構成（6ブロック厳守）】
1. 現状の受容と共感：テーマに合った悩みに共感（毎回ニュアンスを変える）
2. 残酷な現実の宣告：接続詞（ですが/しかし）で空気を変え、その方法が無駄または逆効果と断言（「残酷な事実をお伝えします」は使わない）
3. 具体的な損失の提示：その方法を続けた場合の「最悪の未来」を描写
4. 理論的根拠（Why）：「なぜなら〜」で始め、解剖学・物理学のロジックで説明
5. 真の解決策（What）：「本気で〜になりたいなら」と問いかけ、確実な家トレへの切り替えを提案
6. アクション（結び）：「今から一緒に家トレを3つ頑張っていきましょう！」（この文言で固定）

【文字数】700〜800文字ちょうど（セリフのみ。最後に実際の文字数を括弧で記載する）"""

# テーマ自動生成用のニッチキーワード（30〜50代女性向けダイエット・健康）
AUTO_SEARCH_QUERIES = [
    "30代 40代 50代 女性 ダイエット 最新",
    "更年期 ダイエット 筋トレ トレンド",
    "女性 健康 痩せる 話題",
]


# ── テーマ自動生成（キーワード入力なし） ────────────────────────────
def generate_themes(
    script_type: str,
    used_themes: list,
    rejected_themes: list,
    trends: list,
    video_trends: list,
    youtube_trends: list,
    angle_name: str,
    model: str = "anthropic/claude-sonnet-4-6",
) -> list:
    persona = YOUTUBE_PERSONA if script_type == "youtube" else REEL_PERSONA
    char_range = "4500〜5000文字のYouTube台本" if script_type == "youtube" else "700〜800文字のリール動画台本"

    used_str = "\n".join(f"・{t}" for t in used_themes[-20:]) or "（まだなし）"
    rejected_str = "\n".join(f"・{t}" for t in rejected_themes[-30:]) or "（なし）"
    trend_str = "\n".join(trends) or "（取得できませんでした）"
    video_str = "\n".join(video_trends) or "（取得できませんでした）"
    youtube_str = "\n".join(youtube_trends) or "（取得できませんでした）"

    prompt = f"""{persona}

30〜50代女性向けダイエット・健康系の{char_range}テーマを20個提案してください。

【アングル（切り口）】「{angle_name}」を軸に展開すること

【使用済みテーマ（被らないこと・似たものも避ける）】
{used_str}

【NGテーマ（絶対に提案しないこと）】
{rejected_str}

【Google最新トレンド記事（参考）】
{trend_str}

【YouTube人気動画トレンド（参考）】
{video_str}

【YouTube Data API 人気動画（参考）】
{youtube_str}

【必須ルール】
・20個のうち必ず5個以上は「意外性・逆説・最新研究・珍しい切り口」のテーマにすること
・残り15個はオーソドックスだが新鮮さのあるテーマにすること
・NGテーマと似たものは絶対に出さないこと

【出力形式】
番号付きリストでタイトルのみを20個。説明は不要。
1. テーマタイトル
2. テーマタイトル
...
20. テーマタイトル"""

    response = _call_llm(prompt, model=model, temperature=0.85, max_tokens=2000)
    themes = []
    for line in response.split("\n"):
        line = line.strip()
        if not line:
            continue
        if len(line) > 2 and line[0].isdigit() and ". " in line:
            themes.append(line.split(". ", 1)[1].strip())
        elif len(line) > 2 and line[0].isdigit() and "．" in line:
            themes.append(line.split("．", 1)[1].strip())
    return themes[:20]


def generate_ideas(
    script_type: str,
    selected_themes: list,
    angle_name: str,
    good_elements: list,
    rejected_ideas: list,
    model: str = "anthropic/claude-sonnet-4-6",
) -> list:
    persona = YOUTUBE_PERSONA if script_type == "youtube" else REEL_PERSONA
    structure = YOUTUBE_STRUCTURE if script_type == "youtube" else REEL_STRUCTURE

    themes_str = " / ".join(selected_themes)
    good_str = "\n".join(f"・{e}" for e in good_elements) or "（まだデータなし）"
    rejected_str = "\n".join(f"・{i}" for i in rejected_ideas[-30:]) or "（なし）"

    prompt = f"""{persona}

選ばれたテーマ：「{themes_str}」

このテーマで使えるコンテンツアイデア（エピソード・事例・データ・科学的根拠・切り口）を20個提案してください。

{structure}

【アングル（切り口）】「{angle_name}」を軸にすること

【過去に好評だった要素（積極的に参考にする）】
{good_str}

【NGアイデア（絶対に使わないこと）】
{rejected_str}

【必須ルール】
・20個のうち5個以上は「意外性・最新研究・珍しいデータ・驚きの事実」を含むアイデアにすること

【出力形式】
番号付きリストで1〜2行のアイデアを20個。
1. アイデア内容
2. アイデア内容
...
20. アイデア内容"""

    response = _call_llm(prompt, model=model, temperature=0.75, max_tokens=3000)
    ideas = []
    for line in response.split("\n"):
        line = line.strip()
        if not line:
            continue
        if len(line) > 2 and line[0].isdigit() and ". " in line:
            ideas.append(line.split(". ", 1)[1].strip())
        elif len(line) > 2 and line[0].isdigit() and "．" in line:
            ideas.append(line.split("．", 1)[1].strip())
    return ideas[:20]


def generate_draft(
    script_type: str,
    selected_themes: list,
    selected_ideas: list,
    good_elements: list,
    bad_patterns: list,
    ref_scripts: list,
    model: str = "anthropic/claude-sonnet-4-6",
) -> str:
    persona = YOUTUBE_PERSONA if script_type == "youtube" else REEL_PERSONA
    structure = YOUTUBE_STRUCTURE if script_type == "youtube" else REEL_STRUCTURE

    themes_str = " / ".join(selected_themes)
    ideas_str = "\n".join(f"・{i}" for i in selected_ideas)
    good_str = "\n".join(f"・{e}" for e in good_elements) or "（データなし）"
    bad_str = "\n".join(f"・{p}" for p in bad_patterns) or "（データなし）"

    ref_str = ""
    for i, ref in enumerate(ref_scripts, 1):
        ref_str += f"\n【参考台本{i}（冒頭抜粋）】\n{ref[:800]}\n"

    char_min, char_max = (4500, 5000) if script_type == "youtube" else (700, 800)
    max_tok = 10000 if script_type == "youtube" else 2000

    prompt = f"""{persona}

以下の情報をもとに、完成した台本を作成してください。

【テーマ】{themes_str}

{structure}

【使用するアイデア（これらを盛り込む）】
{ideas_str}

【過去に好評だった要素（積極的に取り入れる）】
{good_str}

【過去に悪評だったパターン（絶対に避ける）】
{bad_str}
{ref_str}

【必須ルール】
・文字数：{char_min}〜{char_max}文字（台本本文のみで計算）
・台本本文のみ出力（説明・補足・メモは不要）
・改行を適切に入れて読みやすくする
・セリフのみ（ト書き・カッコ書きの指示は最小限に）"""

    return _call_llm(prompt, model=model, temperature=0.65, max_tokens=max_tok)


def generate_titles(draft: str, script_type: str,
                    model: str = "anthropic/claude-sonnet-4-6") -> str:
    persona = YOUTUBE_PERSONA if script_type == "youtube" else REEL_PERSONA
    media = "YouTube動画" if script_type == "youtube" else "リール動画"
    draft_excerpt = draft[:1200]

    prompt = f"""{persona}

以下の台本に対して、クリック率・保存率の高い{media}用タイトルを5本と、
サムネイル用キャッチコピーを3本作成してください。

【台本冒頭（参考）】
{draft_excerpt}

【出力形式】
## タイトル候補（5本）
1. タイトル（数字・感情ワード・ベネフィットを入れて35〜45文字）
2. タイトル
3. タイトル
4. タイトル
5. タイトル

## サムネイル用テキスト（3本）
1. キャッチコピー（10〜20文字、インパクト重視）
2. キャッチコピー
3. キャッチコピー"""

    return _call_llm(prompt, model=model, temperature=0.8, max_tokens=1000)


# ── 全情報を並行取得してテーマ生成（UIから呼ぶ） ─────────────────────
def fetch_all_trends() -> tuple:
    """Serper通常検索・動画検索・YouTube Data APIを並行実行"""
    import concurrent.futures
    query_article = AUTO_SEARCH_QUERIES[0]
    query_video = AUTO_SEARCH_QUERIES[1]
    query_yt = AUTO_SEARCH_QUERIES[2]

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        f_trend = executor.submit(get_trends, query_article)
        f_video = executor.submit(get_video_trends, query_video)
        f_youtube = executor.submit(get_youtube_trending, query_yt)
        trends = f_trend.result()
        video_trends = f_video.result()
        youtube_trends = f_youtube.result()

    return trends, video_trends, youtube_trends
