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
# Claudeが混雑時に自動でGPT-4oにフォールバックするモデルリスト
_FALLBACK_MODELS = [
    "gpt-4o",
    "gemini/gemini-2.5-flash",
]

def _build_kwargs(model: str, prompt: str, temperature: float, max_tokens: int) -> dict:
    kwargs = dict(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if model.startswith("xai/"):
        kwargs["api_base"] = "https://api.x.ai/v1"
        kwargs["api_key"] = os.getenv("XAI_API_KEY", "")
    return kwargs

def _call_llm(prompt: str, model: str = "anthropic/claude-sonnet-4-6",
              temperature: float = 0.7, max_tokens: int = 8000) -> str:
    import litellm
    # まず指定モデルで試みる
    last_err = None
    for attempt_model in [model] + _FALLBACK_MODELS:
        try:
            kwargs = _build_kwargs(attempt_model, prompt, temperature, max_tokens)
            response = litellm.completion(**kwargs)
            if attempt_model != model:
                # フォールバックが発動した場合はログに残す
                print(f"[fallback] {model} → {attempt_model}")
            return response.choices[0].message.content
        except Exception as e:
            err_str = str(e).lower()
            # overloaded / rate_limit / server_error のときだけ次のモデルへ
            if any(k in err_str for k in ["overload", "rate_limit", "529", "500", "503"]):
                last_err = e
                continue
            # それ以外のエラー（認証失敗・不正モデル名など）はすぐ上に投げる
            raise
    # 全モデル失敗
    raise last_err


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
【ターゲット】35歳以上の女性。楽な方法に逃げがちだが、本気で体を変えたい主婦・OL・子育て中のママさん。
【最重要ルール】このリール動画は「運動・家トレ・体の動かし方」がメインテーマです。特定の食材・食品・食事メニューの細かいアドバイス（例：〇〇を食べろ・△△を控えろ）は一切含めないこと。ただし、低カロリー食が代謝を落とす・食べないと筋肉が減るなど「運動や代謝に直接つながる食事の話」は問題ない。"""

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
    keyword: str = "",
) -> list:
    persona = YOUTUBE_PERSONA if script_type == "youtube" else REEL_PERSONA
    char_range = "4500〜5000文字のYouTube台本" if script_type == "youtube" else "700〜800文字のリール動画台本"

    used_str = "\n".join(f"・{t}" for t in used_themes[-20:]) or "（まだなし）"
    rejected_str = "\n".join(f"・{t}" for t in rejected_themes[-30:]) or "（なし）"
    trend_str = "\n".join(trends) or "（取得できませんでした）"
    video_str = "\n".join(video_trends) or "（取得できませんでした）"
    youtube_str = "\n".join(youtube_trends) or "（取得できませんでした）"
    keyword_str = f"\n\n【キーワード指定（必ずこのテーマに関連させること）】\n「{keyword}」" if keyword.strip() else ""

    # 40通り固有の切り口定義（10メイン角度 × 4サブ角度）
    ANGLE_SLOTS = [
        # 科学・データ根拠型
        ("science_a", "最新研究で常識を覆す型", "最新論文・臨床データで従来の定説が間違いだったと示す"),
        ("science_b", "比較実験・数値検証型", "AとBを比べた実験や統計で差を可視化する"),
        ("science_c", "体内メカニズム解説型", "ホルモン・代謝・神経の仕組みを「なぜそうなるか」で語る"),
        ("science_d", "専門家警告・見落とされた真実型", "医師や研究者が指摘する多くの人が知らない落とし穴"),
        # 感情・共感型
        ("emotion_a", "あるある共感→反転型", "「頑張ってるのに…」という悔しさに共感し驚きの解決策を提示"),
        ("emotion_b", "誰も教えてくれなかった本音型", "業界の常識・専門家が隠している不都合な事実を暴く"),
        ("emotion_c", "自己肯定感・心理ケア型", "見た目より内側から変わる、自分を責めなくていい理由"),
        ("emotion_d", "将来への恐怖・後悔予防型", "今やらないと10年後こうなる、という未来の自分への警鐘"),
        # 体験談・ストーリー型
        ("story_a", "失敗談から学ぶ反面教師型", "〇〇をやり続けた結果どうなったか、実例で語る"),
        ("story_b", "劇的ビフォーアフター型", "〇〇を変えただけで体が変わった実際のストーリー"),
        ("story_c", "専門家が驚いたケーススタディ型", "臨床や指導現場で実際に起きた意外な事例"),
        ("story_d", "継続できた人・できなかった人の分岐点型", "何が成否を分けたか、具体的な行動の違いで語る"),
        # 常識論破・逆説型
        ("debate_a", "「実は逆効果」暴露型", "良いと思われていた行動が実は逆効果だったと証明する"),
        ("debate_b", "やらなくていい理由型", "頑張らなくていい・やめていい、という解放感のあるテーマ"),
        ("debate_c", "業界の嘘・誤解を正す型", "ダイエット・健康業界が広めてきた誤情報を訂正する"),
        ("debate_d", "常識の盲点・見落とし型", "みんながやってるのに誰も疑わなかった盲点を指摘"),
        # 今すぐ行動型
        ("action_a", "今日から始める具体的ルーティン型", "明日朝から実践できる1つの習慣を提案"),
        ("action_b", "〇〇をやめるだけ型", "足し算でなく「やめる」だけで変わる、低ハードル提案"),
        ("action_c", "緊急性・タイムリミット型", "今の年齢・今の状態だから間に合う、を強調"),
        ("action_d", "小さな変化・積み上げ型", "たった5分・1つだけの小さな行動から始める方法"),
        # 比較・ランキング型
        ("ranking_a", "〇〇vs△△徹底比較型", "2つの方法を同じ条件で比べてどちらが効果的か示す"),
        ("ranking_b", "最強TOP3・ワースト3型", "効果が高い順・悪影響が大きい順にランキングで提示"),
        ("ranking_c", "年代別・体型別・タイプ別最適解型", "あなたのタイプによって正解が違うことを示す"),
        ("ranking_d", "コスパ最強・最短最速型", "同じ結果なら少ない努力・時間で達成できる方法を比較"),
        # ステップ解説型
        ("howto_a", "順番が大事・やる順番型", "手順を間違えると効果がゼロになる正しいシーケンス"),
        ("howto_b", "やってはいけないNG手順型", "多くの人が踏む間違いステップとその正しい代替手順"),
        ("howto_c", "段階別・レベル別攻略型", "初心者→中級者→上級者と段階を分けた最適な進め方"),
        ("howto_d", "時間帯・タイミング別最適化型", "朝・夜・食前・運動後など「いつやるか」で効果が変わる"),
        # 心理・行動経済学型
        ("psychology_a", "損失回避・もったいない心理型", "やめると損する・今の状態を続けると損するを強調"),
        ("psychology_b", "社会的証明・周りの目型", "同世代の〇割が実践、知らないのは自分だけという刺激"),
        ("psychology_c", "習慣化・継続できる仕組み型", "意思力に頼らず続けられる環境・仕組みの作り方"),
        ("psychology_d", "自己イメージ・思い込み書き換え型", "「自分には無理」という信念が体を太らせている理由"),
        # トレンド・時事型
        ("trend_a", "SNS・インフルエンサーに広まる最新情報型", "今TikTok・Instagramで話題の方法の真偽を検証"),
        ("trend_b", "最新研究・2024〜2025年の新発見型", "ここ1〜2年で明らかになった新常識・アップデート情報"),
        ("trend_c", "季節・時期限定の体変化型", "この季節だから起きる体の変化とその対処法"),
        ("trend_d", "海外では当たり前・日本で未普及型", "欧米・韓国では常識なのに日本ではまだ知られていない方法"),
        # 権威・専門家型
        ("expert_a", "医師・栄養士が勧める意外な方法型", "専門資格を持つプロが実際に患者・クライアントに教える方法"),
        ("expert_b", "研究機関・大学の発表型", "〇〇大学の研究・論文が証明した事実として権威性を強調"),
        ("expert_c", "芸能人・著名人が実践して変わった型", "有名人の体験談を切り口に信頼性と親しみやすさを両立"),
        ("expert_d", "現場の指導者だけが知っている裏ノウハウ型", "一般には出回らないトレーナー・指導者の実践知"),
    ]

    # 重複しやすい汎用キーワード（プロンプトで明示的に禁止）
    OVERUSED_KEYWORDS = [
        "有酸素運動", "ランニング", "ウォーキング", "朝の運動", "朝に行う",
        "筋肉痛", "歩き方", "走っても痩せない", "ランニングが痩せない",
        "有酸素運動vs筋トレ", "立ち仕事が運動の代わり",
    ]
    overused_str = "・" + "\n・".join(OVERUSED_KEYWORDS)

    def _gen_one(slot_key: str, slot_name: str, slot_desc: str) -> str:
        prompt = f"""{persona}

30〜50代女性向けダイエット・健康系の{char_range}テーマを1個だけ提案してください。{keyword_str}

【この1テーマに使う切り口】「{slot_name}」
{slot_desc}

【使用済みテーマ（被らないこと）】
{used_str}

【NGテーマ（絶対に提案しないこと）】
{rejected_str}

【禁止キーワード（タイトルにもサブテキストにも一切使わないこと）】
{overused_str}

【参考トレンド】
{trend_str}

【必須ルール】
・切り口「{slot_name}」をそのまま活かしたテーマにすること
・禁止キーワードと意味的に被るテーマ（言い換えも含む）は一切出さないこと
・他の切り口で既に使われそうな汎用テーマ（有酸素/ウォーキング/朝活等）は絶対に避けること
・専門用語は使わず直感的な言葉にすること
・箇条書き3つは「具体的な事実・ホルモン名・数値・メカニズム名・行動」を含めること（「本当の理由」「正しい方法」など曖昧な表現は禁止）

【出力形式】（1行のみ・番号不要・以下の例のような形式で）
例：停滞期が起きる意外な原因｜コルチゾールが代謝を下げる／筋肉量が週1%ずつ減る／3週間で突破できる方法

実際のテーマを1行で出力してください（「テーマタイトル」「ポイント1」などのプレースホルダーはそのまま書かないこと）"""

        resp = _call_llm(prompt, model=model, temperature=0.9, max_tokens=200)
        for line in resp.split("\n"):
            line = line.strip()
            if not line:
                continue
            if len(line) > 2 and line[0].isdigit() and ". " in line:
                line = line.split(". ", 1)[1].strip()
            if line.startswith("例："):
                continue
            if line.startswith("テーマタイトル｜"):
                line = line[len("テーマタイトル｜"):].strip()
                if line and len(line) > 10:
                    return line
                continue
            if line.startswith("テーマタイトル"):
                continue
            if "｜" in line or len(line) > 10:
                return line
        return resp.strip()

    # 40スロットを並列実行
    import concurrent.futures as _cf
    results: list = [""] * len(ANGLE_SLOTS)
    with _cf.ThreadPoolExecutor(max_workers=20) as ex:
        future_map = {
            ex.submit(_gen_one, sk, sn, sd): i
            for i, (sk, sn, sd) in enumerate(ANGLE_SLOTS)
        }
        for fut in _cf.as_completed(future_map):
            idx = future_map[fut]
            try:
                results[idx] = fut.result()
            except Exception:
                results[idx] = ""

    # 重複排除：先頭タイトル部分（｜より前）が類似するものを除く
    def _title_part(t: str) -> str:
        return t.split("｜")[0].strip()

    seen_titles: list[str] = []
    deduped: list[str] = []
    for t in results:
        if not t:
            continue
        tp = _title_part(t)
        # 既出タイトルと4文字以上共通する場合はスキップ
        is_dup = any(
            len(set(tp) & set(s)) >= 4 and (tp in s or s in tp or tp[:6] == s[:6])
            for s in seen_titles
        )
        if not is_dup:
            seen_titles.append(tp)
            deduped.append(t)

    return deduped[:40]


def generate_ideas(
    script_type: str,
    selected_themes: list,
    angle_name: str,
    good_elements: list,
    rejected_ideas: list,
    model: str = "anthropic/claude-sonnet-4-6",
) -> list:
    persona = YOUTUBE_PERSONA if script_type == "youtube" else REEL_PERSONA
    themes_str = " / ".join(selected_themes)
    good_str = "\n".join(f"・{e}" for e in good_elements) or "（まだデータなし）"
    rejected_str = "\n".join(f"・{i}" for i in rejected_ideas[-30:]) or "（なし）"

    # 40通り固有の切り口（8カテゴリ × 5サブ角度）
    IDEA_SLOTS = [
        # データ・研究系
        ("data_a", "最新論文・研究データ型", "直近の科学論文・臨床研究が示す意外な数値や発見"),
        ("data_b", "統計・調査結果型", "大規模調査・アンケートデータが示す実態"),
        ("data_c", "比較実験型", "AとBを同条件で比べた実験・測定結果"),
        ("data_d", "医療現場のデータ型", "病院・クリニックの実際の患者データや診療実績"),
        ("data_e", "海外研究・最新エビデンス型", "欧米・アジアの最新研究が日本の常識を覆す事実"),
        # 失敗・間違い系
        ("mistake_a", "よくある間違いの暴露型", "多くの人がやってしまう定番NG行動とその理由"),
        ("mistake_b", "逆効果の証明型", "良かれと思ってやっていることが実は悪化させている証拠"),
        ("mistake_c", "継続できない理由の分析型", "頑張っても続かない・結果が出ない本当の原因"),
        ("mistake_d", "情報の誤解・デマ検証型", "SNSやネットで広まっている間違った健康情報の訂正"),
        ("mistake_e", "やりすぎ・過剰行動の弊害型", "努力しすぎることで起きる体へのダメージ"),
        # 体験談・事例系
        ("story_a", "成功体験・変化のストーリー型", "実際に〇〇をやめた・変えた結果の具体的な変化"),
        ("story_b", "失敗から学んだ教訓型", "間違った方法を続けた結果どうなったかの反面教師"),
        ("story_c", "専門家の指導現場型", "トレーナー・栄養士が実際のクライアントに教えること"),
        ("story_d", "年代別の実体験型", "30代・40代・50代それぞれが経験する体の変化の実例"),
        ("story_e", "継続できた人の共通点型", "3ヶ月・半年続けられた人が実際にやっていたこと"),
        # 逆説・意外性系
        ("paradox_a", "常識の真逆が正解型", "みんながやっている方法と逆のことが実は効果的"),
        ("paradox_b", "やらない方がいい理由型", "頑張らなくていい・やめた方がいいという驚きの提案"),
        ("paradox_c", "見た目と実態のギャップ型", "痩せて見えるのに不健康、太って見えるのに健康な理由"),
        ("paradox_d", "少ないほど効果的型", "時間・回数・量を減らした方がむしろ結果が出る理由"),
        ("paradox_e", "食べた方が痩せる型", "食べることで代謝が上がる・食べないと逆効果なメカニズム"),
        # 行動提案系
        ("action_a", "今日から1つだけ変える型", "明日の朝から実践できる具体的な1つのアクション"),
        ("action_b", "やめるだけ習慣型", "何かを追加せず「やめる」だけで変わる低ハードルな提案"),
        ("action_c", "5分でできる習慣型", "毎日5分以内で完結する無理のない継続可能な行動"),
        ("action_d", "タイミング・順番の最適化型", "何をするかより「いつ・どの順番で」するかが重要な理由"),
        ("action_e", "環境を変えるだけ型", "意志力に頼らず環境・仕組みを変えることで自動的に続く方法"),
        # 比較・検証系
        ("compare_a", "方法A vs 方法B 徹底比較型", "2つのアプローチを同じ基準で比べてどちらが有効か"),
        ("compare_b", "年代別・体型別の最適解型", "同じことをしても効果が違う理由と個人差の正体"),
        ("compare_c", "コスパ・タイパ最強選び型", "同じ効果なら最小の時間・費用・努力で済む方法"),
        ("compare_d", "プロとアマの差型", "専門家がやることと一般人がやることの決定的な違い"),
        ("compare_e", "成功者と失敗者の行動比較型", "結果が出た人と出なかった人の実際の行動の差"),
        # 心理・習慣系
        ("psych_a", "続かない心理的原因型", "やる気ではなく脳・心理のメカニズムが邪魔している理由"),
        ("psych_b", "自己肯定感と体の関係型", "ストレス・自己否定が体重・体型に与える科学的影響"),
        ("psych_c", "習慣化の脳科学型", "行動を無意識化する脳の仕組みと習慣定着のコツ"),
        ("psych_d", "食欲・過食の心理型", "なぜ食べ過ぎてしまうのかの心理・神経学的なメカニズム"),
        ("psych_e", "モチベーション不要型", "やる気がなくても続けられる仕組みと考え方"),
        # 時事・トレンド系
        ("trend_a", "SNSで話題の方法の真偽検証型", "TikTok・Instagramで流行している方法を科学的に検証"),
        ("trend_b", "海外で流行・日本上陸型", "欧米・韓国で実践されている最新トレンドとその効果"),
        ("trend_c", "季節・気候と体の関係型", "この時期特有の体の変化とその対処法"),
        ("trend_d", "最新ガジェット・ツール活用型", "スマートウォッチ・アプリ・最新ツールを使った効率化"),
        ("trend_e", "医学の最新常識アップデート型", "ここ数年で変わった医学的見解・新しい推奨基準"),
    ]

    def _gen_one(slot_key: str, slot_name: str, slot_desc: str) -> str:
        prompt = f"""{persona}

選ばれたテーマ：「{themes_str}」

このテーマに関するコンテンツアイデアを1個だけ提案してください。

【この1アイデアに使う切り口】「{slot_name}」
{slot_desc}

【過去に好評だった要素（参考に）】
{good_str}

【NGアイデア（絶対に使わないこと）】
{rejected_str}

【必須ルール】
・切り口「{slot_name}」を活かした具体的なアイデアにすること
・専門用語は使わず初心者でも直感的にわかる言葉にすること
・視聴者が「これ自分のことだ」「知りたい！」と思える表現にすること
・箇条書き3つは「具体的な事実・ホルモン名・数値・メカニズム名・行動」を含めること（「正しい方法」「改善のヒント」など曖昧な表現は禁止）

【出力形式】（1行のみ・番号不要）
例：食べる量を減らしても痩せない本当の理由｜レプチン分泌が減り食欲が増す／筋肉量が月3%減少する／1日100kcal増やすだけで改善

実際のアイデアを1行で出力してください（「アイデア内容」などプレースホルダーはそのまま書かないこと）"""

        resp = _call_llm(prompt, model=model, temperature=0.9, max_tokens=200)
        for line in resp.split("\n"):
            line = line.strip()
            if not line:
                continue
            if len(line) > 2 and line[0].isdigit() and ". " in line:
                line = line.split(". ", 1)[1].strip()
            if line.startswith("例："):
                continue
            if line.startswith("アイデア内容｜") or line == "アイデア内容":
                line = line[len("アイデア内容｜"):].strip() if "｜" in line else ""
                if line and len(line) > 10:
                    return line
                continue
            line = line.replace("**", "").replace("*", "")
            if "｜" in line or len(line) > 10:
                return line
        return resp.strip().replace("**", "").replace("*", "")

    import concurrent.futures as _cf
    results: list = [""] * len(IDEA_SLOTS)
    with _cf.ThreadPoolExecutor(max_workers=20) as ex:
        future_map = {
            ex.submit(_gen_one, sk, sn, sd): i
            for i, (sk, sn, sd) in enumerate(IDEA_SLOTS)
        }
        for fut in _cf.as_completed(future_map):
            idx = future_map[fut]
            try:
                results[idx] = fut.result()
            except Exception:
                results[idx] = ""

    # 重複排除：先頭タイトル部分（｜より前）が類似するものを除く
    def _title_part(t: str) -> str:
        return t.split("｜")[0].strip()

    seen_titles: list[str] = []
    deduped: list[str] = []
    for t in results:
        if not t:
            continue
        tp = _title_part(t)
        is_dup = any(
            len(set(tp) & set(s)) >= 4 and (tp in s or s in tp or tp[:6] == s[:6])
            for s in seen_titles
        )
        if not is_dup:
            seen_titles.append(tp)
            deduped.append(t)

    return deduped[:40]


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


# 5種類のアングル（切り口）で台本を並列生成
DRAFT_ANGLES = [
    ("science",    "科学・データ根拠型",   "最新研究・統計・科学的データを中心に、冷静な論理で読者を説得する。数値・出典・研究名を積極的に盛り込む"),
    ("emotion",    "感情・共感型",         "読者の深い悩みや感情に寄り添い、感動・涙・共鳴で心を動かす。感情語を多用し、「わかる」「そうだよね」の共感を積み重ねる"),
    ("story",      "体験談・ストーリー型", "実際の体験談・成功例・失敗談を軸に、物語として展開する。登場人物・状況・転換点・結末の起承転結で引き込む"),
    ("debate",     "常識論破・逆説型",     "視聴者が「え？」と驚く逆説・意外な事実から始め、常識を覆す衝撃展開で最後まで引き込む"),
    ("action",     "今すぐ行動型",         "今やらないと損・後悔するという緊急性を最初から強調し、具体的なアクションを即座に起こしたくさせる"),
    ("ranking",    "比較・ランキング型",   "「第1位」「TOP3」などランキング形式で比較・選択肢を提示し、どれが自分に合うか判断させる構成にする"),
    ("howto",      "ステップ解説型",       "「ステップ1・2・3」など具体的な手順・やり方を丁寧に解説し、今日から実践できる内容に特化する"),
    ("psychology", "心理・行動経済学型",   "損失回避・社会的証明・希少性など人間の心理バイアスを活用し、自然と行動したくなる心理的仕掛けを随所に入れる"),
    ("trend",      "トレンド・時事型",     "最新トレンド・話題のニュース・季節感と絡めて「今だから見るべき」旬な切り口で展開する"),
    ("expert",     "権威・専門家型",       "著名な専門家・研究者・成功者の言葉・実績・論文を前面に出し、「専門家も推薦」という信頼と権威で引き込む"),
]

def generate_draft_variants(
    script_type: str,
    selected_themes: list,
    selected_ideas: list,
    good_elements: list,
    bad_patterns: list,
    ref_scripts: list,
    model: str = "anthropic/claude-sonnet-4-6",
    edit_improvements: list = None,
) -> list:
    """10種のアングルで台本を並列生成。[{"angle_key","angle_name","draft"},...] を返す"""
    import concurrent.futures

    persona = YOUTUBE_PERSONA if script_type == "youtube" else REEL_PERSONA
    structure = YOUTUBE_STRUCTURE if script_type == "youtube" else REEL_STRUCTURE
    themes_str = " / ".join(selected_themes)
    ideas_str = "\n".join(f"・{i}" for i in selected_ideas)
    good_str = "\n".join(f"・{e}" for e in good_elements) or "（データなし）"
    bad_str = "\n".join(f"・{p}" for p in bad_patterns) or "（データなし）"
    # ユーザー編集から学習した改善ルール
    improvements = edit_improvements or []
    improve_str = "\n".join(f"・{r}" for r in improvements[-20:]) if improvements else ""
    ref_str = ""
    for i, ref in enumerate(ref_scripts, 1):
        ref_str += f"\n【参考台本{i}（冒頭抜粋）】\n{ref[:600]}\n"
    char_min, char_max = (4500, 5000) if script_type == "youtube" else (700, 800)
    max_tok = 10000 if script_type == "youtube" else 2000

    def _gen_one(angle_key, angle_name, angle_desc):
        improve_section = f"""
【✨ユーザーの編集履歴から学んだ改善ルール（最優先で反映すること）】
{improve_str}
""" if improve_str else ""

        prompt = f"""{persona}

以下の情報をもとに、【{angle_name}】の切り口で完成した台本を作成してください。

【切り口の特徴】{angle_desc}

【テーマ】{themes_str}

{structure}

【使用するアイデア（これらを盛り込む）】
{ideas_str}

【過去に好評だった要素（積極的に取り入れる）】
{good_str}

【過去に悪評だったパターン（絶対に避ける）】
{bad_str}
{improve_section}{ref_str}

【必須ルール】
・文字数：{char_min}〜{char_max}文字
・台本本文のみ出力（説明・補足不要）
・改行を適切に入れて読みやすく"""
        try:
            draft = _call_llm(prompt, model=model, temperature=0.72, max_tokens=max_tok)
        except Exception as e:
            draft = f"（生成エラー: {e}）"
        return {"angle_key": angle_key, "angle_name": angle_name, "draft": draft, "summary": []}

    def _gen_summary(item: dict) -> dict:
        """台本からこの切り口ならではの特徴的な点を3行で生成する"""
        draft = item.get("draft", "")
        if not draft or draft.startswith("（生成エラー"):
            return item
        angle_name = item.get("angle_name", "")
        prompt = f"""以下は【{angle_name}】という切り口で作られた台本です。

【台本（抜粋）】
{draft[:900]}

この切り口【{angle_name}】だからこそ使われている「独自の視点・根拠・アプローチ・具体的な方法」を3行で書いてください。

【厳守ルール】
・「〇〇はリバウンドする」「食べないと痩せない」のような、どの台本にも共通する一般論は絶対に書かない
・この切り口【{angle_name}】でしか語れない具体的な内容・手法・視点だけを書く
・数字・ホルモン名・具体的な行動・メカニズム名など「この台本ならでは」の具体情報を必ず含める
・各行は45文字以内
・「・」で始まる3行だけ出力（前置き・説明・タイトル等は一切不要）"""
        try:
            resp = _call_llm(prompt, model="anthropic/claude-sonnet-4-6",
                             temperature=0.6, max_tokens=200)
            lines = []
            for line in resp.split("\n"):
                line = line.strip().lstrip("・●▶→- 　").strip()
                if len(line) >= 10:
                    lines.append(line[:55] + ("…" if len(line) > 55 else ""))
                if len(lines) >= 3:
                    break
            item["summary"] = lines
        except Exception:
            item["summary"] = []
        return item

    def _dedup_summaries(results: list) -> list:
        """全カード間で重複・類似している箇条書きを除去する"""
        # 全サマリーの先頭10文字を集計して、3枚以上に登場するものを「共通文」とみなす
        from collections import Counter
        prefix_count: Counter = Counter()
        for item in results:
            seen = set()
            for line in item.get("summary", []):
                key = line[:10]
                if key not in seen:
                    prefix_count[key] += 1
                    seen.add(key)

        # 3枚以上に出現するprefixは共通すぎるので除去
        common_prefixes = {k for k, v in prefix_count.items() if v >= 3}

        for item in results:
            unique = [
                line for line in item.get("summary", [])
                if line[:10] not in common_prefixes
            ]
            # 除去後に空になった場合は元のリストを維持（最低1行は見せる）
            item["summary"] = unique if unique else item.get("summary", [])[:1]
        return results

    # ── Step1: 台本を10本並列生成 ─────────────────────────────────────
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(_gen_one, ak, an, ad) for ak, an, ad in DRAFT_ANGLES]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    # ── Step2: 切り口ならではのサマリーを10本並列生成 ────────────────
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        sum_futures = [ex.submit(_gen_summary, item) for item in results]
        results = [f.result() for f in concurrent.futures.as_completed(sum_futures)]

    # ── Step3: 全カード間で重複する文を除去 ─────────────────────────
    results = _dedup_summaries(results)

    # DRAFT_ANGLESの順番で並び替え
    order = {ak: i for i, (ak, _, _) in enumerate(DRAFT_ANGLES)}
    results.sort(key=lambda x: order.get(x["angle_key"], 99))
    return results


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


# ── セクション別台本ビルダー ──────────────────────────────────────────

REEL_SECTIONS = ["冒頭フック", "共感・問題提起", "権威・解決策提示", "メインコンテンツ", "行動喚起（CTA）"]
YOUTUBE_SECTIONS = ["オープニング", "問題提起・共感", "権威・概要説明", "解説①", "解説②", "解説③", "まとめ・CTA"]


def split_script_sections(script: str, script_type: str,
                          model: str = "anthropic/claude-sonnet-4-6") -> list:
    """台本をセクション名ごとに分割してリストで返す"""
    sections = REEL_SECTIONS if script_type == "reel" else YOUTUBE_SECTIONS
    sections_str = "\n".join(f"{i+1}. {s}" for i, s in enumerate(sections))
    prompt = f"""以下の台本を、指定のセクション名ごとに分割してください。
各セクションの内容をそのまま抜き出してください（加工しない）。

【セクション名（必ずこの順序で）】
{sections_str}

【台本】
{script}

【出力形式】各セクションを以下の区切り文字で分けて出力：
===SECTION: セクション名===
セクション本文
===END===

全セクション分出力してください。内容が空でも必ず出力してください。"""
    try:
        text = _call_llm(prompt, model=model, temperature=0.1, max_tokens=5000)
        result = []
        import re
        blocks = re.findall(r'===SECTION: (.+?)===\s*(.*?)\s*===END===', text, re.DOTALL)
        for name, content in blocks:
            result.append({"name": name.strip(), "content": content.strip()})
        # 見つからなかったセクションは空で補完
        found_names = {r["name"] for r in result}
        for s in sections:
            if s not in found_names:
                result.append({"name": s, "content": ""})
        return result
    except Exception:
        # 分割失敗時はシンプルに均等分割
        lines = script.split("\n")
        chunk = max(1, len(lines) // len(sections))
        return [{"name": s, "content": "\n".join(lines[i*chunk:(i+1)*chunk])}
                for i, s in enumerate(sections)]


def generate_section_variants(section_name: str, section_content: str,
                              context_before: str, script_type: str,
                              model: str = "anthropic/claude-sonnet-4-6",
                              n: int = 5) -> list:
    """セクションの5つの候補バリアントを1回のLLM呼び出しで生成"""
    type_name = "リール台本（700〜800文字全体）" if script_type == "reel" else "YouTube台本（4500〜5000文字全体）"
    context_str = f"\n【直前のセクション（文脈）】\n{context_before[-400:]}\n" if context_before else ""

    prompt = f"""あなたは{type_name}のプロのライターです。
以下のセクション「{section_name}」に対して、{n}つの【まったく異なるアプローチ】の候補を作成してください。{context_str}
【現在のセクション内容（参考）】
{section_content}

【最重要ルール：候補の多様性】
各候補は以下のように、切り口・トーン・構成を根本的に変えてください：
- 候補1: データ・数字・科学的根拠を前面に出す理性的アプローチ
- 候補2: 体験談・ストーリー・感情に訴えかける共感アプローチ
- 候補3: 常識を覆す・意外性で引き込む逆説アプローチ
- 候補4: 問いかけ・対話形式で読者を巻き込むインタラクティブアプローチ
- 候補5: 緊急性・危機感を煽って行動を促す切迫アプローチ

【出力ルール】
- 各候補は「候補1:」「候補2:」...「候補{n}:」で始める
- 各候補は改行で分けてすぐ内容を書く（見出しや説明は不要）
- 似たような表現・同じ書き出し・同じ構成は絶対に避ける
- {type_name}全体の文字数バランスを考慮した分量にする
- 台本本文のみ（ト書きなし）

候補1:から候補{n}:の順に出力してください。"""
    try:
        text = _call_llm(prompt, model=model, temperature=0.85, max_tokens=3000)
        import re
        pattern = r'候補\d+[:：]\s*(.*?)(?=候補\d+[:：]|$)'
        matches = re.findall(pattern, text, re.DOTALL)
        variants = [m.strip() for m in matches if m.strip()]
        # 足りない場合は元のコンテンツで補完
        while len(variants) < n:
            variants.append(section_content)
        return variants[:n]
    except Exception:
        return [section_content] * n


# ── 4モデル並列ファクトチェック ────────────────────────────────────────

FC_MODELS = [
    ("anthropic/claude-sonnet-4-6", "Claude Sonnet 4.6",   "🟣"),
    ("gpt-4o",                      "ChatGPT (GPT-4o)",    "🟢"),
    ("gemini/gemini-2.5-flash",     "Gemini 2.5 Flash",    "🔵"),
    ("xai/grok-3-mini",             "Grok 3 Mini",         "⚫"),
]

FC_PROMPT_TEMPLATE = """あなたは優秀なファクトチェッカーです。以下の台本に含まれる事実的な主張を検証してください。

【台本】
{script}

【重要なルール】
- ⚠️要注意と判定した主張は、確定的・断定的な表現を避け「〜の可能性があります」「〜とされる場合もあります」「〜と言われています」など、可能性・傾向として表現してください
- 具体的な数字・統計・データについて、独自に正確性を確認できなかった場合は、その数字をそのまま引用・断定せず「詳細な数値は確認が難しい状況です」「おおよその傾向として〜が考えられます」などと表現してください
- ✅正確と確信を持って言えるもの以外は、断定的な言い切りを避けてください

【出力形式（必ずこの形式で）】
## 総合判定: [✅ 概ね正確 / ⚠️ 一部要注意 / ❌ 問題あり]

## 検証結果
各主張について:
### 主張: [主張内容を短く]
- 判定: ✅正確 / ⚠️要注意 / ❌誤り
- 根拠: [確認した内容。要注意の場合は可能性・傾向として表現し、未確認の数字は引用しない]
- 修正案: [問題ある場合のみ]

## 総評（2〜3文）"""


def factcheck_with_model(script: str, model: str, model_name: str) -> dict:
    """単一モデルでファクトチェックを実行"""
    prompt = FC_PROMPT_TEMPLATE.format(script=script[:3000])
    try:
        text = _call_llm(prompt, model=model, temperature=0.2, max_tokens=4000)
        # 総合判定を抽出
        import re
        m = re.search(r'総合判定.*?(✅|⚠️|❌)', text)
        verdict = m.group(1) if m else "❓"
        return {"model_name": model_name, "verdict": verdict, "text": text, "error": None}
    except Exception as e:
        return {"model_name": model_name, "verdict": "❓", "text": "", "error": str(e)}


def factcheck_parallel(script: str) -> list:
    """4モデルを並列実行してファクトチェック結果リストを返す"""
    import concurrent.futures
    results = [None] * len(FC_MODELS)

    def _run(idx, model_id, model_name, icon):
        r = factcheck_with_model(script, model_id, model_name)
        r["icon"] = icon
        results[idx] = r

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futures = [ex.submit(_run, i, mid, mname, icon)
                   for i, (mid, mname, icon) in enumerate(FC_MODELS)]
        concurrent.futures.wait(futures)
    return results


# ── ファクトチェック自動修正 ──────────────────────────────────────────

def auto_correct_script(original: str, fc_results: list, model: str = "anthropic/claude-sonnet-4-6") -> dict:
    """4モデルのFC結果を統合して自動修正版テキストを生成する"""
    # 各モデルの問題指摘をまとめる
    issues_text = ""
    for r in fc_results:
        if r and not r.get("error") and r.get("text"):
            issues_text += f"\n\n=== {r['model_name']} の指摘 ===\n{r['text']}"

    prompt = f"""あなたは優秀な台本編集者です。
以下の【元の台本】に対して、4つのAIがファクトチェックを行いました。
その結果を参考に、問題のある表現・数字・事実を修正した【修正版台本】を作成してください。

【元の台本】
{original}

【ファクトチェック結果（4AI）】
{issues_text}

【修正のルール】
- ❌「明確に誤り」「そのようなデータは存在しない」「事実として成立しない」と判定された箇所は、その文・センテンスごと台本から完全に削除する（言い換えや曖昧化ではなく削除）
- ⚠️要注意のうち「データや数値が実際に間違っている」と指摘された箇所は正しい表現に修正する
- ⚠️要注意のうち「可能性としてあり得る・科学的に否定しきれない」と判定された箇所は修正しない（そのまま残す）
- ✅正確と判定された箇所は変更しない
- 文体・全体の流れは元の台本を維持する（削除により文章がつながらなくなる場合は自然につなぎ直す）
- 修正箇所が分かるよう、変更した部分の説明も最後に箇条書きで添える（削除した箇所は「削除」と明記）

【出力形式】
## 修正版台本
（修正した台本の全文）

## 修正箇所の説明
- （変更点1）
- （変更点2）
..."""

    try:
        text = _call_llm(prompt, model=model, temperature=0.2, max_tokens=4000)
        # 修正版台本と説明を分離
        import re
        script_match = re.search(r'## 修正版台本\s*\n(.*?)(?=\n## |\Z)', text, re.DOTALL)
        changes_match = re.search(r'## 修正箇所の説明\s*\n(.*?)(?=\n## |\Z)', text, re.DOTALL)
        corrected = script_match.group(1).strip() if script_match else text
        changes = changes_match.group(1).strip() if changes_match else ""
        return {"corrected": corrected, "changes": changes, "error": None}
    except Exception as e:
        return {"corrected": "", "changes": "", "error": str(e)}


# ── AI討論型ファクトチェック ─────────────────────────────────────────────

_DISCUSSION_AGENTS = [
    ("Claude",  "anthropic/claude-sonnet-4-6",  "🟣", "left",  "#7C3AED", "#F5F3FF"),
    ("ChatGPT", "gpt-4o",                       "🟢", "right", "#059669", "#ECFDF5"),
    ("Grok",    "xai/grok-3-mini",              "⚫", "left",  "#374151", "#F3F4F6"),
    ("Gemini",  "gemini/gemini-2.5-flash",      "🔵", "right", "#1D4ED8", "#EFF6FF"),
]

_R1_PROMPTS = {
    "Claude": """あなたはAI「Claude」です。ChatGPT・Grok・Geminiと一緒に台本のファクトチェック討論をしています。
以下の台本を読んで、事実として問題がある箇所・根拠の薄い数字・誇大な主張を具体的に指摘してください。
他のAIへ話しかける会話口調で書いてください（200〜280字程度）。

【台本】
{script}""",

    "ChatGPT": """あなたはAI「ChatGPT」として討論に参加しています。
Claudeの指摘内容に対して同意・反論・補足しながら、あなた自身が見つけた追加の問題点も述べてください（200〜280字）。

【これまでの討論】
{history}""",

    "Grok": """あなたはAI「Grok」として討論に参加しています。
ClaudeとChatGPTの議論を受けて、率直に補足・反論・新たな視点を加えてください。
2人が見落としている点や過剰指摘だと思う点があれば遠慮なく言ってください（200〜280字）。

【これまでの討論】
{history}""",

    "Gemini": """あなたはAI「Gemini」として討論に参加しています。
3人の議論を整理して、修正が最も必要な箇所を優先順位付けし、あなた独自の視点も加えてください（200〜280字）。

【これまでの討論】
{history}""",
}

_R2_PROMPTS = {
    "Claude": """あなたはAI「Claude」です。ここまでの討論を踏まえて、台本への具体的な修正提案を3つ以内にまとめてください。
「〇〇という表現を△△に変える」という具体的な形で提案してください（200〜280字）。

【これまでの討論】
{history}""",

    "ChatGPT": """あなたはAI「ChatGPT」です。Claudeの修正提案に対して賛成・修正意見・追加提案を述べてください。
合意形成を意識して、最終的にどう直すべきかをまとめてください（200〜280字）。

【これまでの討論】
{history}""",

    "Grok": """あなたはAI「Grok」です。討論の締めくくりとして、絶対に直すべき最重要ポイントを1〜2点だけ断言してください（150〜200字）。

【これまでの討論】
{history}""",

    "Gemini": """あなたはAI「Gemini」です。全員の意見を統合し、修正の優先順位と最終結論を出してください。
この討論の議長として締めの発言をしてください（200〜280字）。

【これまでの討論】
{history}""",
}


def factcheck_discussion(script: str) -> list:
    """4AIが順番に2回ずつ発言するファクトチェック討論（計8メッセージ）。
    各AIは前の発言を読んで返答する。順次実行。
    Returns: list of message dicts
    """
    messages = []
    script_excerpt = script[:2500]

    def _history():
        if not messages:
            return "（まだ発言なし）"
        return "\n\n".join(
            f"【{m['agent']}（Round{m['round']}）】{m['message']}"
            for m in messages
        )

    for round_num, prompts in enumerate([_R1_PROMPTS, _R2_PROMPTS], 1):
        for agent_name, model_id, icon, side, color, bg in _DISCUSSION_AGENTS:
            tmpl = prompts[agent_name]
            prompt = tmpl.format(script=script_excerpt, history=_history())
            try:
                text = _call_llm(prompt, model=model_id, temperature=0.75, max_tokens=600)
            except Exception as e:
                text = f"（応答エラー: {e}）"
            messages.append({
                "agent": agent_name,
                "model": model_id,
                "icon": icon,
                "side": side,
                "color": color,
                "bg": bg,
                "message": text.strip(),
                "round": round_num,
            })

    return messages


def auto_correct_from_discussion(original: str, discussion: list,
                                  model: str = "anthropic/claude-sonnet-4-6") -> dict:
    """AI討論の全指摘を元に台本を自動修正する"""
    discussion_text = "\n\n".join([
        f"【{m['agent']} Round{m['round']}】{m['message']}"
        for m in discussion
    ])

    prompt = f"""あなたは台本編集の専門家です。
4つのAIが以下の台本についてファクトチェック討論を行いました。
討論で指摘された問題点を全て反映した修正版台本を作成してください。

【元の台本】
{original}

【AI討論の内容】
{discussion_text}

【修正ルール】
- 討論で複数のAIが「明確に誤り」「そのようなデータは存在しない」「事実として成立しない」と合意した箇所は、その文・センテンスごと台本から完全に削除する（言い換えや曖昧化ではなく削除）
- 討論で「データや数値が実際に間違っている」と指摘された箇所は正しい表現に修正する
- 討論で「可能性としてあり得る・科学的に否定しきれない・要注意だが一定の根拠がある」と判定された箇所は修正しない（そのまま残す）
- 問題なしと合意された箇所は変更しない
- 文体・構成・全体の流れは元の台本を維持する（削除により文章がつながらなくなる場合は自然につなぎ直す）

【出力形式】
## 修正版台本
（修正した全文をそのまま）

## 修正箇所の説明
- （元の表現 → 修正後の表現、の形式で箇条書き）"""

    try:
        text = _call_llm(prompt, model=model, temperature=0.2, max_tokens=6000)
        import re
        script_match = re.search(r'## 修正版台本\s*\n(.*?)(?=\n## |\Z)', text, re.DOTALL)
        changes_match = re.search(r'## 修正箇所の説明\s*\n(.*?)(?=\n## |\Z)', text, re.DOTALL)
        corrected = script_match.group(1).strip() if script_match else text
        changes = changes_match.group(1).strip() if changes_match else ""
        return {"corrected": corrected, "changes": changes, "error": None}
    except Exception as e:
        return {"corrected": "", "changes": "", "error": str(e)}


def generate_next_fc_message(script: str, messages: list) -> dict | None:
    """討論の次の1メッセージだけを生成して返す（逐次チャット表示用）。
    messagesは現在までの発言リスト。8件で討論完了→Noneを返す。
    """
    total = len(messages)
    if total >= 8:
        return None

    round_num = total // 4 + 1   # 1 or 2
    agent_idx = total % 4        # 0–3

    agent_name, model_id, icon, side, color, bg = _DISCUSSION_AGENTS[agent_idx]
    prompts = _R1_PROMPTS if round_num == 1 else _R2_PROMPTS

    def _history():
        if not messages:
            return "（まだ発言なし）"
        return "\n\n".join(
            f"【{m['agent']}（Round{m['round']}）】{m['message']}"
            for m in messages
        )

    prompt = prompts[agent_name].format(script=script[:2500], history=_history())
    try:
        text = _call_llm(prompt, model=model_id, temperature=0.75, max_tokens=600)
    except Exception as e:
        text = f"（応答エラー: {e}）"

    return {
        "agent": agent_name,
        "icon": icon,
        "side": side,
        "color": color,
        "bg": bg,
        "message": text.strip(),
        "round": round_num,
    }


# ── 追加修正指示による改訂 ────────────────────────────────────────────

def revise_with_instruction(
    current_text: str,
    instruction: str,
    original: str = "",
    model: str = "anthropic/claude-sonnet-4-6",
) -> dict:
    """ユーザーの指示に基づいて修正済み文章をさらに改訂する"""
    original_section = f"\n【元の台本（参考）】\n{original}\n" if original else ""

    prompt = f"""あなたは優秀な台本編集者です。
以下の【現在の文章】に対して、【修正指示】の内容を反映した改訂版を作成してください。{original_section}
【現在の文章】
{current_text}

【修正指示】
{instruction}

【ルール】
- 指示された箇所のみを変更する
- 指示されていない部分は変えない
- 文体・全体の流れを維持する
- 変更した箇所の説明を最後に箇条書きで添える

【出力形式】
## 改訂版
（改訂した文章の全文）

## 変更箇所
- （変更点1）
- （変更点2）
..."""

    try:
        text = _call_llm(prompt, model=model, temperature=0.2, max_tokens=4000)
        import re
        revised_match = re.search(r'## 改訂版\s*\n(.*?)(?=\n## |\Z)', text, re.DOTALL)
        changes_match = re.search(r'## 変更箇所\s*\n(.*?)(?=\n## |\Z)', text, re.DOTALL)
        revised = revised_match.group(1).strip() if revised_match else text
        changes = changes_match.group(1).strip() if changes_match else ""
        return {"revised": revised, "changes": changes, "error": None}
    except Exception as e:
        return {"revised": "", "changes": "", "error": str(e)}


# ── FC後バリアント生成 ────────────────────────────────────────────────

_FC_VARIANT_ANGLES = [
    ("emotion",    "感情・共感型",         "読者の深い悩みや感情に寄り添い、感動・共鳴で心を動かす。感情語を多用し「わかる」「そうだよね」の共感を積み重ねる"),
    ("story",      "体験談・ストーリー型", "実際の体験談・成功例・失敗談を軸に、ドラマティックなストーリーで引き込む。具体的な人物・場面描写を重視する"),
    ("debate",     "常識論破・逆説型",     "視聴者が「え？」と驚く逆説・意外な事実・常識破りの切り口から入る。冒頭で強烈な問いや否定から始める"),
    ("action",     "今すぐ行動型",         "今やらないと損・後悔するという緊急性と即効性を全面に押し出す。行動を促すCTAを随所に盛り込む"),
    ("psychology", "心理・行動経済学型",   "損失回避・社会的証明・希少性など人間心理の法則を活用。「なぜ人はこうしてしまうのか」という心理的視点から解説する"),
]


def generate_fc_variants(
    base_script: str,
    n: int = 3,
    model: str = "anthropic/claude-sonnet-4-6",
) -> list:
    """ファクトチェック済み台本を元に、異なる角度で3バリアントを並列生成する"""
    import concurrent.futures
    import random

    angles = random.sample(_FC_VARIANT_ANGLES, min(n, len(_FC_VARIANT_ANGLES)))
    char_count = len(base_script)

    def _gen_one(angle_key, angle_name, angle_desc):
        prompt = f"""以下の【ベース台本】を元に、【切り口】の方向で書き直した新しい台本を生成してください。

【ベース台本】
{base_script}

【切り口】{angle_name}
{angle_desc}

【ルール】
- ベース台本に含まれる事実・数字はそのまま維持する（ファクトチェック済みのため変更禁止）
- 構成・表現・アプローチを【切り口】に合わせて大きく変える
- 文字数はベース台本（約{char_count}文字）と同程度を目安にする
- 台本本文のみ出力（説明・前置き不要）"""
        try:
            text = _call_llm(prompt, model=model, temperature=0.85, max_tokens=4000)
            return {"angle_key": angle_key, "angle_name": angle_name, "text": text, "error": None}
        except Exception as e:
            return {"angle_key": angle_key, "angle_name": angle_name, "text": "", "error": str(e)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as ex:
        futures = [ex.submit(_gen_one, ak, an, ad) for ak, an, ad in angles]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    return results


# ── 部分ブラッシュアップ ──────────────────────────────────────────────

def generate_brushup_candidates(
    target_text: str,
    instruction: str,
    n_candidates: int,
    script_type: str,
    model: str,
) -> list:
    """台本の一部を指定の方向性で書き直した候補をn個返す"""
    type_name = "YouTube台本（長尺・4500〜5000文字）" if script_type == "youtube" else "リール台本（短尺・700〜800文字）"
    char_count = len(target_text)
    prompt = f"""あなたは{type_name}のプロのライターです。
以下の【元のテキスト】を、【改善の指示】に沿って「表現・言い回し・ニュアンス」だけを変えてください。

【元のテキスト】（{char_count}文字）
{target_text}

【改善の指示】
{instruction}

【絶対に守るルール】
- 文章構成（段落数・段落の順序・話の流れ）は変えない
- 伝えている情報・事実・内容は変えない（削除・追加・入れ替え禁止）
- 文字数は元のテキストの±20%以内に収める（大幅な増減禁止）
- 変えていいのは「言い回し・表現・ニュアンス・語尾・言葉の選び方」のみ
- {n_candidates}パターンの候補を生成する
- 各候補は「---候補N---」という区切り行で分ける（Nは番号）
- 区切り行と候補テキスト以外の説明・前置きは一切不要

出力例:
---候補1---
（書き直したテキスト）
---候補2---
（書き直したテキスト）"""

    text = _call_llm(prompt, model=model, temperature=0.85, max_tokens=3000)

    candidates = []
    import re
    parts = re.split(r"---候補\d+---", text)
    for p in parts:
        p = p.strip()
        if p and len(p) > 10:
            candidates.append(p)

    # パース失敗時は全文を1候補として返す
    if not candidates:
        candidates = [text.strip()]

    return candidates[:n_candidates]


def analyze_brushup_replacements(
    replacements: list,  # [{"original_before": "...", "chosen": "..."}]
    script_type: str,
    model: str,
) -> list:
    """差し替えペアからNGパターンを抽出して返す（今後の生成で避けるべき表現）"""
    if not replacements:
        return []
    type_name = "YouTube台本" if script_type == "youtube" else "リール台本"
    pairs_text = "\n\n".join([
        f"【修正前】\n{r['original_before']}\n\n【修正後】\n{r['chosen']}"
        for r in replacements
    ])
    prompt = f"""以下は{type_name}の「修正前→修正後」のペアです。
修正前の文章に含まれていた「問題のある表現・パターン・書き方」を分析し、
今後の台本生成で避けるべきNGパターンを箇条書きでリストアップしてください。

{pairs_text}

【出力ルール】
- 「〜という表現は避ける」「〜のような書き方はNG」という形式で具体的に
- 10件以内
- 箇条書き（各行を「- 」で始める）
- 説明や前置きは不要、箇条書きのみ出力"""
    text = _call_llm(prompt, model=model, temperature=0.3, max_tokens=800)
    patterns = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith(("-", "•", "・", "●")):
            p = line.lstrip("-•・● ").strip()
            if p:
                patterns.append(p)
    return patterns[:10]


# ── 台本の評価・分析 ──────────────────────────────────────────────────

def analyze_good_elements(script: str, script_type: str, model: str) -> list:
    """好評台本から効果的だったポイントを2〜3個抽出してリストで返す"""
    type_name = "YouTube台本（4500〜5000文字）" if script_type == "youtube" else "リール台本（700〜800文字）"
    prompt = f"""以下の{type_name}を読んで、特に効果的だった構成・表現・手法を2〜3個、簡潔な日本語の箇条書きで抽出してください。

【抽出のポイント】
- 冒頭のフック手法（例：「○○という衝撃データを提示して引き込む」）
- 構成の工夫（例：「問題提起→共感→解決策→行動促進の流れ」）
- 訴求の強さ（例：「数字・体験談を組み合わせた信頼感の出し方」）

箇条書きのみを返してください（・で始まる形式で）。説明文・見出し・前置きは不要。

--- 台本 ---
{script[:2000]}
---"""
    try:
        text = _call_llm(prompt, model=model, temperature=0.3, max_tokens=300)
        elements = []
        for line in text.split("\n"):
            line = line.strip().lstrip("・-•* 　").strip()
            if line and len(line) > 5:
                elements.append(line)
        return elements[:3]
    except Exception:
        return []


def analyze_edit_improvements(
    original: str, edited: str, script_type: str, model: str
) -> list:
    """元台本とユーザー編集後台本を比較し、改善ルールを3〜5個抽出してリストで返す"""
    type_name = "YouTube台本" if script_type == "youtube" else "リール台本"
    # 長すぎる場合は冒頭と末尾を抜粋
    orig_excerpt = original[:1200] + ("\n...(省略)...\n" + original[-400:] if len(original) > 1600 else "")
    edit_excerpt = edited[:1200] + ("\n...(省略)...\n" + edited[-400:] if len(edited) > 1600 else "")

    prompt = f"""あなたは{type_name}の品質改善を専門とするコーチです。
以下の「修正前」と「修正後」の台本を比較し、ユーザーがどのような改善を行ったかを分析してください。

【修正前（AI生成版）】
{orig_excerpt}

【修正後（ユーザー編集版）】
{edit_excerpt}

【分析してほしいこと】
ユーザーが行った編集から「次回のAI生成に活かすべき改善ルール」を3〜5個抽出してください。

【出力形式】（箇条書きのみ・各30〜60文字・前置き不要）
・ルール1
・ルール2
・ルール3
（例：「冒頭の数字データは具体的な研究名と年を必ず添える」「体験談は一人称で語りかける形式にする」）"""

    try:
        text = _call_llm(prompt, model=model, temperature=0.3, max_tokens=400)
        rules = []
        for line in text.split("\n"):
            line = line.strip().lstrip("・-•* 　123456789.").strip()
            if line and len(line) > 8:
                rules.append(line)
        return rules[:5]
    except Exception:
        return []


def consolidate_improvement_rules(
    current_rules: list, new_rules: list, script_type: str, model: str
) -> list:
    """既存ルール＋新ルールをAIが統合・精製して常に最良20件を維持する"""
    # 重複除去して結合
    combined = list(current_rules)
    for r in new_rules:
        if r not in combined:
            combined.append(r)

    # 20件以下なら精製不要
    if len(combined) <= 20:
        return combined

    type_name = "YouTube台本" if script_type == "youtube" else "リール台本"
    rules_str = "\n".join(f"{i+1}. {r}" for i, r in enumerate(combined))

    prompt = f"""あなたは{type_name}の改善専門家です。
以下の改善ルール一覧を分析し、次の3つの作業を行ってください：
1. 似た内容・重複するルールを1つに統合（より具体的・明確な表現にする）
2. 矛盾するルールは重要度の高い方を残す
3. 最終的に最も重要な20件に絞り込む

【改善ルール一覧】
{rules_str}

【出力形式】
箇条書き（・で始まる）で20件以内を出力。前置き・説明・番号は不要。
各ルールは30〜70文字で具体的に記述すること。

・ルール
・ルール
..."""

    try:
        text = _call_llm(prompt, model=model, temperature=0.2, max_tokens=700)
        refined = []
        for line in text.split("\n"):
            line = line.strip().lstrip("・-•* 　123456789.）)").strip()
            if line and len(line) > 8:
                refined.append(line)
        return refined[:20] if refined else combined[-20:]
    except Exception:
        # 失敗時は最新20件にフォールバック
        return combined[-20:]


def analyze_bad_pattern(script: str, script_type: str, bad_note: str, model: str) -> str:
    """悪評台本から改善すべきパターンを1行で返す"""
    type_name = "YouTube台本" if script_type == "youtube" else "リール台本"
    note_text = f"\n【ユーザーコメント】: {bad_note}" if bad_note else ""
    prompt = f"""以下の{type_name}が不評でした。{note_text}
次回避けるべきパターンを1行（30文字以内）で簡潔に記述してください。
文章のみ返してください（例：「感情訴求が弱く論理だけで説得力不足」）。

--- 台本（冒頭のみ）---
{script[:800]}
---"""
    try:
        text = _call_llm(prompt, model=model, temperature=0.3, max_tokens=80)
        return text.strip().split("\n")[0][:60]
    except Exception:
        return ""


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
