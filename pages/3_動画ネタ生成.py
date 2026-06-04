import html as html_module
import concurrent.futures
import random
import requests
import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

# ──────────────────────────────────────────────────────────────
# 視点リスト（研究レベル・専門特化）
# ──────────────────────────────────────────────────────────────
ANGLES = [
    "AMPKキナーゼ活性化と脂肪酸β酸化シグナル経路の制御機構",
    "FGF21（線維芽細胞増殖因子21）による肝臓-脂肪組織クロストーク",
    "mTORC1シグナルと脂肪生成転写因子SREBP-1cの制御機構",
    "PPARα/γ核内受容体リガンドによる脂肪代謝遺伝子の転写調節",
    "エクソソーム・細胞外小胞を介した脂肪組織間シグナル伝達",
    "脂肪組織低酸素環境とHIF-1α誘導性線維化・代謝障害",
    "SIRT1・SIRT3依存性脱アセチル化による脂肪代謝制御",
    "腸内バクテリオファージ（ファージ）と宿主の肥満表現型",
    "胆汁酸受容体FXR・TGR5シグナルとエネルギー代謝調節",
    "終末糖化産物（AGEs）とRAGE受容体による脂肪組織機能障害",
    "前駆脂肪細胞の分化制御とニッチ環境の最新知見",
    "エンドカンナビノイドシステムのCB1受容体と脂肪蓄積機序",
    "H3K27acヒストンアセチル化と代謝遺伝子エピゲノム制御",
    "セラミドde novo合成と脂肪細胞インスリンシグナル障害",
    "UCP1・UCP3ミトコンドリアアンカップリングタンパク質と熱産生",
    "脂肪組織内制御性T細胞（Treg）による代謝性炎症制御",
    "リン脂質リモデリングと脂肪細胞膜流動性・受容体機能",
    "アシルカルニチンプロファイルと不完全ミトコンドリアβ酸化",
    "GIP受容体シグナルと脂肪組織特異的グルコース取り込み",
    "脂肪細胞オートファジー（リポファジー）と中性脂肪分解機構",
    "腸内ウイルソームのバイオマス変動とエネルギー代謝への影響",
    "GPR41・GPR43短鎖脂肪酸受容体と脂肪細胞エネルギー調節",
    "メタボロミクスによる女性特異的脂質代謝バイオマーカー解析",
    "脂肪組織マクロファージのM1/M2極性化と代謝炎症カスケード",
    "RNAスプライシング変異と代謝関連遺伝子の機能的多様性",
    "ミトコンドリア膜電位と脂肪酸輸送タンパクCPT1活性の調節",
    "脂肪酸シンターゼ（FASN）と細胞内脂質プール制御",
    "インクレチン受容体GLP-1R・GIPR以外の新規代謝受容体シグナル",
    "脂肪組織交感神経支配と神経ペプチドによる脂肪分解調節",
]

SYSTEM_PROMPT = """あなたは代謝医学・脂質生化学・分子栄養学の最先端研究者です。
30代〜50代女性の体脂肪を減らすための動画コンテンツのネタ（アイデアの種）を提案します。

【絶対に出力禁止 — 一般化・陳腐化しているネタ】
以下は一般ユーザーにもすでに知られており、動画ネタとして価値がないため完全に排除：

■ 食品・成分系
・カプサイシン・唐辛子の代謝促進
・ポリフェノール全般（レスベラトロール・アントシアニン・カテキン含む）
・ω-3脂肪酸・魚油・DHA・EPA（一般化済み）
・MCTオイル・ケトジェニック（一般化済み）
・発酵食品・乳酸菌（一般化済み）

■ ライフスタイル・環境系
・エストロゲン・女性ホルモン全般
・ブルーライト・光環境・サーカディアンリズム（一般化済み）
・寒冷刺激・冷水・冷温交代浴・低温療法
・マインドフルネス・瞑想・ストレス管理
・睡眠の質・深睡眠（一般化済み）
・コルチゾール・ストレスホルモン（一般化済み）

■ 代謝・体組成系
・腸内環境・腸活・腸内細菌（一般化済み）
・褐色脂肪・ベージュ脂肪（SNSで拡散済み）
・インスリン抵抗性（一般化済み）
・慢性炎症・抗炎症（一般化済み）
・概日リズム・時間栄養学（一般化済み）
・血糖スパイク・低GI食（一般化済み）

→ 上記および「それに近しいもの」「それを少し言い換えたもの」も全て禁止

【出力すること】
・今この瞬間も30代〜50代の日本人女性の体の中で実際に起きているメカニズム
・しかし一般の女性はその存在すら知らない、専門家しか知らない現象
・「自分の体でそんなことが起きていたの！？」と驚けるような内容
・専門用語を使い、研究論文を読む人でないとわからないレベルの知識
・科学的根拠が存在するもの（推測・エセ科学は禁止）
・珍しすぎて一般女性の体と関係ない稀な症例はNG。あくまで「普通の女性の体で起きていること」

【出力形式】
必ず以下の形式で3〜5個出すこと：

・[ネタタイトル：専門用語を含みつつ、何の話かが伝わる1〜2行]
　ひとこと解説：[専門用語の意味を補足しながら、このネタが「何についての話か」を2文で説明する。読んだ人が「なるほど、〇〇の話ね」と理解できるレベル]
　→ 例え：[小学生でもわかる日常のたとえで2〜3文]

【ひとこと解説の書き方ルール】
・専門用語は残してよいが、括弧で一言補足を入れる　例：「AMPK（細胞のエネルギーセンサー）」
・「これは〇〇の話で、〜という仕組みに関係しています」のように、話の全体像がわかるように書く
・難解な論文の要約ではなく、動画を企画する人が内容を理解できるレベルで書く

良い例：
・PPARγ核内受容体のリガンド結合が引き起こす前駆脂肪細胞の不可逆的分化
　ひとこと解説：PPARγ（脂肪細胞を作る司令塔タンパク質）にある物質が結合すると、まだ脂肪細胞になっていない細胞が「もう脂肪細胞になるしかない」状態に固定されてしまう仕組みの話です。この現象が40代以降の女性で起きやすい理由があります。
　→ 例え：体の中に「脂肪細胞の候補生」がいます。司令塔に鍵が刺さった瞬間、候補生は引き返せなくなる。その鍵を何が作るか、という話です。

・日本語のみ
・「ひとこと解説：」と「→ 例え：」は必ず毎回入れること"""

AGENT_ORDER = ["Claude", "ChatGPT", "Gemini", "Grok"]

AGENT_META = {
    "Claude":  {"color": "#a78bfa", "glow": "167, 139, 250", "icon": "◆"},
    "ChatGPT": {"color": "#34d399", "glow": "52, 211, 153",  "icon": "◆"},
    "Gemini":  {"color": "#60a5fa", "glow": "96, 165, 250",  "icon": "◆"},
    "Grok":    {"color": "#fbbf24", "glow": "251, 191, 36",  "icon": "◆"},
}

# ──────────────────────────────────────────────────────────────
# Serper検索
# ──────────────────────────────────────────────────────────────
def search_serper(query: str) -> str:
    api_key = os.getenv("SERPER_API_KEY", "")
    if not api_key:
        return "（Serper未設定）"
    try:
        res = requests.post(
            "https://google.serper.dev/search",
            json={"q": query, "gl": "jp", "hl": "ja", "num": 6},
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            timeout=15,
        )
        data = res.json()
        snippets = [
            f"・{item.get('title','')}: {item.get('snippet','')}"
            for item in data.get("organic", [])[:6]
        ]
        return "\n".join(snippets) if snippets else "検索結果なし"
    except Exception as e:
        return f"検索エラー: {e}"

# ──────────────────────────────────────────────────────────────
# プロンプト構築
# ──────────────────────────────────────────────────────────────
def build_prompt(angle: str, search_results: str, seed: str | None) -> str:
    if seed:
        return f"""【深掘りの起点】
{seed}

【担当視点】
{angle}

【最新検索情報（参考）】
{search_results}

上記のネタをベースに、同じ方向性でさらに深掘り・展開させた専門的なアイデアの種を3〜5個出してください。
一般的な内容は排除し、研究レベルの専門性で。"""
    return f"""【担当視点】
{angle}

【最新検索情報（参考）】
{search_results}

この視点から、30代〜50代女性の体脂肪減少に関する、研究レベルの専門的なアイデアの種を3〜5個出してください。"""

# ──────────────────────────────────────────────────────────────
# 各AI生成関数
# ──────────────────────────────────────────────────────────────
def gen_claude(angle, search_results, seed):
    from anthropic import Anthropic
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_prompt(angle, search_results, seed)}],
    )
    return msg.content[0].text


def gen_chatgpt(angle, search_results, seed):
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    res = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1024,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(angle, search_results, seed)},
        ],
    )
    return res.choices[0].message.content


def gen_gemini(angle, search_results, seed):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY", ""))
    full_prompt = SYSTEM_PROMPT + "\n\n" + build_prompt(angle, search_results, seed)
    res = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=full_prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=2048,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return res.text


def gen_grok(angle, search_results, seed):
    from openai import OpenAI
    client = OpenAI(
        api_key=os.getenv("XAI_API_KEY", ""),
        base_url="https://api.x.ai/v1",
    )
    res = client.chat.completions.create(
        model="grok-3",
        max_tokens=1024,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(angle, search_results, seed)},
        ],
    )
    return res.choices[0].message.content


GEN_FUNCS = {
    "Claude": gen_claude, "ChatGPT": gen_chatgpt,
    "Gemini": gen_gemini, "Grok": gen_grok,
}

# ──────────────────────────────────────────────────────────────
# 審査員（Claude Sonnet 4.6）によるランキング
# ──────────────────────────────────────────────────────────────
JUDGE_PROMPT = """あなたは動画コンテンツの企画専門家です。
4つのAIが「30代〜50代の日本人女性の体脂肪を減らす」をテーマに出したアイデアを評価してください。

【評価基準】
以下の2軸で評価し、両方を満たすものを高評価にすること：

① 実際に起きているか（関連性）
・30代〜50代の日本人女性の体の中で、今この瞬間も実際に起きているメカニズムか
・特殊な病気・稀な体質・一部の人にしか起きないことはNG
・ごく普通の日本人女性なら誰でも体験していることが理想

② 知られていないか（希少性）
・一般の30代〜50代女性がその存在を全く知らないものほど高評価
・SNSやテレビ・雑誌ですでに広まっているものは低評価
・「自分の体でそんなことが起きていたの！？」という驚きがあるものが最高評価

【最高評価の定義】
「普通の日本人女性の体で確実に起きているが、本人はまったく知らない現象」

【出力形式】（必ずこの形式で出力すること）

🥇 1位：[AI名]
テーマ：[そのAIが出したネタの中で最も親和性が高いもの、1行で]
理由：[30〜50代日本人女性への当てはまりやすさの観点で2〜3文]

🥈 2位：[AI名]
テーマ：[同上]
理由：[同上]

🥉 3位：[AI名]
テーマ：[同上]
理由：[同上]

4位：[AI名]
テーマ：[同上]
理由：[同上]

【一言総評】
[全体を通じて一言]
"""

def _build_judge_input(results: dict) -> str:
    contents = ""
    for name in AGENT_ORDER:
        if name in results:
            contents += f"\n\n【{name}のアイデア】\n{results[name]['content']}"
    return f"以下の4つのアイデアを評価してください：{contents}"

def run_judge_claude(results: dict) -> str:
    from anthropic import Anthropic
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=JUDGE_PROMPT,
        messages=[{"role": "user", "content": _build_judge_input(results)}],
    )
    return msg.content[0].text

def format_judge(text: str, color: str) -> str:
    """ランキングテキストを均一なHTMLカードに変換する"""
    MEDALS = {"1": "🥇", "2": "🥈", "3": "🥉", "4": "4️⃣"}
    RANK_LABELS = {"1": "1位", "2": "2位", "3": "3位", "4": "4位"}

    lines = [l.strip() for l in text.splitlines()]
    blocks = []
    current = {}

    for line in lines:
        if not line:
            continue
        # 順位行の検出（🥇〜 or 4位： などのパターン）
        rank_num = None
        for num in ["1", "2", "3", "4"]:
            if (f"{num}位" in line) and ("位：" in line or "位: " in line):
                rank_num = num
                break
        if rank_num:
            if current:
                blocks.append(current)
            ai_name = line.split("：")[-1].split(":")[-1].strip()
            current = {"rank": rank_num, "ai": ai_name, "theme": "", "reason": ""}
        elif line.startswith("テーマ"):
            val = line.split("：")[-1].split(":")[-1].strip()
            current["theme"] = val
        elif line.startswith("理由"):
            val = line.split("：")[-1].split(":")[-1].strip()
            current["reason"] = val
        elif current.get("reason") and not line.startswith("【"):
            # 理由の続き
            current["reason"] += " " + line
        elif line.startswith("【一言総評】") or line.startswith("一言総評"):
            if current:
                blocks.append(current)
                current = {}
            blocks.append({"rank": "summary", "text": ""})
        elif blocks and blocks[-1].get("rank") == "summary":
            blocks[-1]["text"] += line + " "

    if current:
        blocks.append(current)

    html = ""
    for b in blocks:
        if b.get("rank") == "summary":
            txt = html_module.escape(b.get("text", "").strip())
            html += f"""
<div style="margin-top:20px; padding:14px 16px; background:rgba(255,255,255,0.03);
     border-left:3px solid {color}; border-radius:0 8px 8px 0;">
  <div style="font-size:10px; font-weight:700; letter-spacing:0.1em; color:{color}; margin-bottom:6px;">一言総評</div>
  <div style="font-size:13px; color:#e2e8f0; line-height:1.7;">{txt}</div>
</div>"""
        else:
            rank = b.get("rank", "")
            medal = MEDALS.get(rank, "")
            label = RANK_LABELS.get(rank, f"{rank}位")
            ai    = html_module.escape(b.get("ai", ""))
            theme = html_module.escape(b.get("theme", ""))
            reason = html_module.escape(b.get("reason", ""))
            html += f"""
<div style="display:flex; gap:14px; margin-bottom:20px; align-items:flex-start;">
  <div style="font-size:26px; line-height:1; flex-shrink:0; padding-top:2px;">{medal}</div>
  <div style="flex:1;">
    <div style="font-size:12px; font-weight:700; color:{color}; letter-spacing:0.05em; margin-bottom:4px;">{label}　{ai}</div>
    {"" if not theme else f'<div style="font-size:12px; color:#e2e8f0; background:rgba(255,255,255,0.05); border-radius:6px; padding:5px 10px; margin-bottom:6px;">{theme}</div>'}
    <div style="font-size:13px; color:#e2e8f0; line-height:1.75;">{reason}</div>
  </div>
</div>"""
    return html

def run_judge_chatgpt(results: dict) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    res = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1200,
        messages=[
            {"role": "system", "content": JUDGE_PROMPT},
            {"role": "user", "content": _build_judge_input(results)},
        ],
    )
    return res.choices[0].message.content

# ──────────────────────────────────────────────────────────────
# 単体再生成（1つのAIだけ指示付きで再生成）
# ──────────────────────────────────────────────────────────────
def build_refine_prompt(original_content: str, instruction: str, history: list[str] | None = None) -> str:
    history_section = ""
    if history:
        history_section = "【これまでの改善指示の履歴】\n"
        for i, h in enumerate(history, 1):
            history_section += f"  {i}回目：{h}\n"
        history_section += "\n"

    return f"""{history_section}【現在の出力（直前のバージョン）】
---
{original_content}
---

【今回の新しい指示】
{instruction}

上記の履歴・現在の出力・今回の指示をすべて踏まえて、改善したバージョンを出力してください。
出力形式は同じ形式（専門的なネタ + → 例え：）を維持すること。"""


def run_all_brush_up(results: dict, instruction: str, history: list[str] | None = None) -> dict:
    """全AIに指示履歴＋今回の指示を渡して一括再生成する"""
    new_results = {}
    def refine_one(name):
        original = results[name]["content"]
        prompt = build_refine_prompt(original, instruction, history)
        return _call_ai(name, prompt)

    def _call_ai(name, prompt):
        from anthropic import Anthropic
        from openai import OpenAI
        from google import genai as _genai
        from google.genai import types as _types
        if name == "Claude":
            client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            msg = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        elif name == "ChatGPT":
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            res = client.chat.completions.create(
                model="gpt-4o", max_tokens=1024,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            )
            return res.choices[0].message.content
        elif name == "Gemini":
            client = _genai.Client(api_key=os.getenv("GOOGLE_API_KEY", ""))
            res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=SYSTEM_PROMPT + "\n\n" + prompt,
                config=_types.GenerateContentConfig(
                    max_output_tokens=1024,
                    thinking_config=_types.ThinkingConfig(thinking_budget=0),
                ),
            )
            return res.text
        elif name == "Grok":
            client = OpenAI(api_key=os.getenv("XAI_API_KEY", ""), base_url="https://api.x.ai/v1")
            res = client.chat.completions.create(
                model="grok-3", max_tokens=1024,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
            )
            return res.choices[0].message.content
        return "⚠️ 不明なAI名"

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(refine_one, name): name for name in AGENT_ORDER if name in results}
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                content = future.result()
            except Exception as e:
                content = f"⚠️ エラー\n{e}"
            new_results[name] = {"content": content, "angle": results[name]["angle"]}
    return new_results


# ──────────────────────────────────────────────────────────────
# AI出力をHTML形式に整形
# ──────────────────────────────────────────────────────────────
def format_content(text: str) -> str:
    """箇条書きと例えをきれいなHTMLに変換する"""
    lines = text.splitlines()
    html_parts = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        # 箇条書き行（・ - * • で始まる）
        if line.startswith(("・", "-", "*", "•", "●")):
            bullet_text = line.lstrip("・-*•● ").strip()
            escaped = html_module.escape(bullet_text)
            html_parts.append(
                f'<div class="idea-item">'
                f'<span class="idea-bullet">・</span>'
                f'<span class="idea-text">{escaped}</span>'
                f'</div>'
            )
        # ひとこと解説行
        elif line.startswith("ひとこと解説"):
            eg_text = line.split("：", 1)[-1].strip()
            escaped = html_module.escape(eg_text)
            html_parts.append(
                f'<div class="idea-summary">'
                f'<span class="summary-label">💡 解説</span>'
                f'<span class="summary-text">{escaped}</span>'
                f'</div>'
            )
        # 例え行（→ や例え：で始まる）
        elif line.startswith(("→", "→", "例え", "　→")):
            eg_text = line.lstrip("→　 ").strip()
            if eg_text.startswith("例え："):
                eg_text = eg_text[3:].strip()
            escaped = html_module.escape(eg_text)
            html_parts.append(
                f'<div class="idea-example">'
                f'<span class="example-label">→ 例え</span>'
                f'<span class="example-text">{escaped}</span>'
                f'</div>'
            )
        # 番号付き（1. 2. など）
        elif len(line) > 2 and line[0].isdigit() and line[1] in ".、)）":
            item_text = line[2:].strip()
            escaped = html_module.escape(item_text)
            html_parts.append(
                f'<div class="idea-item">'
                f'<span class="idea-bullet">・</span>'
                f'<span class="idea-text">{escaped}</span>'
                f'</div>'
            )
        else:
            escaped = html_module.escape(line)
            html_parts.append(f'<div class="idea-plain">{escaped}</div>')
        i += 1
    return "\n".join(html_parts)

# ──────────────────────────────────────────────────────────────
# 全AI並列実行
# ──────────────────────────────────────────────────────────────
def run_all(seed: str | None = None) -> dict:
    angles = random.sample(ANGLES, 4)
    angle_map = {name: angles[i] for i, name in enumerate(AGENT_ORDER)}
    query = (
        f"{seed} 分子メカニズム 脂肪代謝 最新研究 女性 論文"
        if seed
        else "脂肪代謝 分子メカニズム 最新研究 2024 2025 女性 論文 専門"
    )
    search_results = search_serper(query)
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futures = {
            ex.submit(GEN_FUNCS[name], angle_map[name], search_results, seed): name
            for name in AGENT_ORDER
        }
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                content = future.result()
            except Exception as e:
                content = f"⚠️ エラー\n{e}"
            results[name] = {"content": content, "angle": angle_map[name]}
    return results


def run_all_with_judge(seed: str | None = None) -> tuple[dict, str, str]:
    results = run_all(seed)
    # 2つの審査員を並列実行
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        f_claude  = ex.submit(run_judge_claude, results)
        f_chatgpt = ex.submit(run_judge_chatgpt, results)
        judge_claude  = f_claude.result()
        judge_chatgpt = f_chatgpt.result()
    return results, judge_claude, judge_chatgpt

# ──────────────────────────────────────────────────────────────
# Streamlit UI
# ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="動画ネタ生成", page_icon="⬡", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif !important; }

[data-testid="stAppViewContainer"] {
    background: radial-gradient(ellipse at 20% 0%, #0f0820 0%, #06060f 40%, #080818 100%);
    min-height: 100vh;
}
[data-testid="stHeader"]  { background: transparent !important; }
[data-testid="stSidebar"] { background: #07070f !important; }
[data-testid="stSidebarContent"] { background: #07070f !important; }

/* ページ全体のパディング調整 */
.block-container { padding-top: 2rem !important; max-width: 1400px; }

/* ヘッダー */
.page-header {
    text-align: center;
    padding: 48px 0 16px;
}
.page-title {
    font-size: 32px;
    font-weight: 700;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, #e2d9f3 0%, #a78bfa 40%, #60a5fa 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 8px;
}
.page-subtitle {
    font-size: 13px;
    color: #4b5563;
    letter-spacing: 0.05em;
}

/* 区切り線 */
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #1e1e38, transparent);
    margin: 28px 0;
}

/* ランダム生成ボタン */
div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #6d28d9, #4f46e5) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 12px 32px !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    letter-spacing: 0.03em !important;
    box-shadow: 0 0 24px rgba(109, 40, 217, 0.4), 0 4px 16px rgba(0,0,0,0.4) !important;
    transition: all 0.2s ease !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    box-shadow: 0 0 36px rgba(109, 40, 217, 0.6), 0 4px 24px rgba(0,0,0,0.5) !important;
    transform: translateY(-1px) !important;
}

/* セカンダリボタン */
div[data-testid="stButton"] > button[kind="secondary"] {
    background: rgba(255,255,255,0.04) !important;
    color: #6b7280 !important;
    border: 1px solid #1f2937 !important;
    border-radius: 8px !important;
    font-size: 12px !important;
}

/* 深掘りボタン */
div[data-testid="stButton"] > button:not([kind]) {
    background: rgba(96, 165, 250, 0.1) !important;
    color: #60a5fa !important;
    border: 1px solid rgba(96, 165, 250, 0.3) !important;
    border-radius: 10px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
}
div[data-testid="stButton"] > button:not([kind]):hover {
    background: rgba(96, 165, 250, 0.2) !important;
    border-color: rgba(96, 165, 250, 0.5) !important;
}

/* テキスト入力 */
[data-testid="stTextInput"] input {
    background: #ffffff !important;
    border: 1px solid #1e1e38 !important;
    border-radius: 12px !important;
    color: #000000 !important;
    font-size: 14px !important;
    padding: 12px 16px !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #4f46e5 !important;
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.15) !important;
}
[data-testid="stTextInput"] input::placeholder { color: #9ca3af !important; }

/* アイデアカード */
.idea-card {
    position: relative;
    border-radius: 20px;
    padding: 28px 30px;
    margin-bottom: 16px;
    background: linear-gradient(145deg, #0c0c1e 0%, #0f0f24 100%);
    border: 1px solid rgba(255,255,255,0.04);
    overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.idea-card:hover {
    transform: translateY(-2px);
}
.card-glow-bar {
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    border-radius: 20px 20px 0 0;
}
.card-header-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;
}
.card-agent-name {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}
.card-angle-tag {
    font-size: 10px;
    color: #374151;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 20px;
    padding: 3px 10px;
    line-height: 1.4;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.card-content {
    font-size: 13.5px;
    line-height: 1.6;
    color: #e2e8f0;
    border-top: 1px solid rgba(255,255,255,0.06);
    padding-top: 16px;
}
.idea-item {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    margin-bottom: 10px;
}
.idea-bullet {
    color: #6366f1;
    font-size: 15px;
    flex-shrink: 0;
    margin-top: 1px;
}
.idea-text {
    color: #e2e8f0;
    line-height: 1.7;
}
.idea-summary {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    margin: 6px 0 8px 16px;
    padding: 8px 12px;
    background: rgba(99, 102, 241, 0.07);
    border-left: 2px solid rgba(99, 102, 241, 0.5);
    border-radius: 0 6px 6px 0;
}
.summary-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: #818cf8;
    white-space: nowrap;
    margin-top: 2px;
    flex-shrink: 0;
}
.summary-text {
    font-size: 13px;
    color: #e2e8f0;
    line-height: 1.7;
}
.idea-example {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    margin-bottom: 16px;
    margin-left: 16px;
    padding: 8px 12px;
    background: rgba(255,255,255,0.03);
    border-left: 2px solid rgba(99, 102, 241, 0.3);
    border-radius: 0 6px 6px 0;
}
.example-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: #6366f1;
    white-space: nowrap;
    margin-top: 2px;
    flex-shrink: 0;
}
.example-text {
    font-size: 12.5px;
    color: #e2e8f0;
    line-height: 1.6;
}
.idea-plain {
    color: #e2e8f0;
    font-size: 12.5px;
    margin-bottom: 4px;
    line-height: 1.6;
}

/* 指示欄ラベル */
.refine-label {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin: 10px 0 6px;
    opacity: 0.7;
}

/* 履歴バー */
.history-row {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
    padding: 12px 0 4px;
}
.history-label {
    font-size: 10px;
    color: #374151;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-right: 4px;
}
.history-chip {
    font-size: 11px;
    color: #4b5563;
    background: rgba(255,255,255,0.03);
    border: 1px solid #1a1a2e;
    border-radius: 20px;
    padding: 3px 12px;
}
.history-arrow { color: #1f2937; font-size: 12px; }

/* ランキングセクション */
.judge-section {
    background: linear-gradient(145deg, #0c0c20, #10102a);
    border-radius: 20px;
    padding: 28px 32px;
    box-shadow: 0 0 40px rgba(167, 139, 250, 0.05), 0 8px 32px rgba(0,0,0,0.4);
}
.judge-section-claude  { border: 1px solid rgba(167, 139, 250, 0.2); }
.judge-section-chatgpt { border: 1px solid rgba(52, 211, 153, 0.2); }
.judge-header {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.judge-header-claude  { color: #a78bfa; }
.judge-header-chatgpt { color: #34d399; }
.judge-header::after {
    content: '';
    flex: 1;
    height: 1px;
}
.judge-header-claude::after  { background: linear-gradient(90deg, rgba(167,139,250,0.3), transparent); }
.judge-header-chatgpt::after { background: linear-gradient(90deg, rgba(52,211,153,0.3), transparent); }
.judge-body {
    font-size: 14px;
    line-height: 1.8;
    color: #e2e8f0;
}

/* 空状態 */
.empty-state {
    text-align: center;
    padding: 80px 0;
    color: #1f2937;
    font-size: 14px;
    letter-spacing: 0.05em;
}

/* セクションラベル */
.section-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #374151;
    margin-bottom: 10px;
}

/* Streamlit要素の色調整 */
h1, h2, h3, p, label { color: #e2e8f0 !important; }
[data-testid="stMarkdownContainer"] p { color: #6b7280 !important; }
</style>
""", unsafe_allow_html=True)

# ── セッション初期化 ──
for key, default in [
    ("results", {}), ("history", []),
    ("judge_claude", ""), ("judge_chatgpt", ""),
    ("brush_log", []),   # ブラッシュアップの指示履歴
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── ヘッダー ──
st.markdown("""
<div class="page-header">
  <div class="page-title">動画ネタ生成システム</div>
  <div class="page-subtitle">4 AI AGENTS · RESEARCH-LEVEL · FAT LOSS · WOMEN 30–50</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ── フェーズ1：ランダム生成 ──
col_main, col_pad = st.columns([1, 3])
with col_main:
    if st.button("⬡　ランダムでネタを生成", type="primary", use_container_width=True):
        with st.spinner("検索中 + 4AI 同時生成中 + 審査中..."):
            st.session_state.results, st.session_state.judge_claude, st.session_state.judge_chatgpt = run_all_with_judge(seed=None)
            st.session_state.history = ["RANDOM"]

st.markdown("<br>", unsafe_allow_html=True)

# ── フェーズ2：深掘り ──
st.markdown('<div class="section-label">気に入ったネタを入力して深掘りする</div>', unsafe_allow_html=True)
col_inp, col_btn = st.columns([5, 1])
with col_inp:
    seed_input = st.text_input(
        "seed",
        placeholder="例）FGF21を介した肝臓-脂肪組織クロストークと女性の内臓脂肪",
        label_visibility="collapsed",
    )
with col_btn:
    st.markdown("<div style='padding-top:2px'>", unsafe_allow_html=True)
    refine_clicked = st.button("深掘り →", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

if refine_clicked:
    if seed_input.strip():
        with st.spinner("関連研究を検索中 + 4AI 深掘り中 + 審査中..."):
            st.session_state.results, st.session_state.judge_claude, st.session_state.judge_chatgpt = run_all_with_judge(seed=seed_input.strip())
            st.session_state.history.append(seed_input.strip())
    else:
        st.warning("ネタを入力してください。")

# ── 履歴表示 ──
if st.session_state.history:
    chips_html = '<div class="history-row"><span class="history-label">FLOW</span>'
    for i, h in enumerate(st.session_state.history):
        if i > 0:
            chips_html += '<span class="history-arrow">›</span>'
        chips_html += f'<span class="history-chip">{html_module.escape(h)}</span>'
    chips_html += "</div>"
    st.markdown(chips_html, unsafe_allow_html=True)

    col_r, col_sp = st.columns([1, 5])
    with col_r:
        if st.button("リセット", type="secondary", use_container_width=True):
            st.session_state.history = []
            st.session_state.results = {}
            st.session_state.judge_claude = ""
            st.session_state.judge_chatgpt = ""
            st.session_state.brush_log = []
            st.rerun()

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ── 結果表示 ──
if st.session_state.results:

    # ── ① ブラッシュアップ入力（最上部） ──
    st.markdown('<div class="section-label">全AIへの指示 — ブラッシュアップ</div>', unsafe_allow_html=True)

    if st.session_state.brush_log:
        for entry in st.session_state.brush_log:
            st.markdown(f"""
<div style="display:flex; gap:10px; align-items:flex-start; margin-bottom:8px;">
  <div style="background:#1e1e38; border-radius:20px 20px 4px 20px; padding:9px 16px;
       font-size:13px; color:#e2e8f0; max-width:80%;">
    {html_module.escape(entry)}
  </div>
</div>""", unsafe_allow_html=True)

    b_col1, b_col2 = st.columns([5, 1])
    with b_col1:
        brush_input = st.text_input(
            "brush",
            placeholder="例）40代女性が共感しやすい方向に絞って / 例えをもっとわかりやすく / 腸以外の視点で",
            label_visibility="collapsed",
            key="brush_input_field",
        )
    with b_col2:
        brush_clicked = st.button("全AI指示 →", use_container_width=True, key="brush_btn")

    if brush_clicked:
        if brush_input.strip():
            with st.spinner("全AIが指示に従って再生成中 + 審査中..."):
                new_results = run_all_brush_up(
                    st.session_state.results,
                    brush_input.strip(),
                    history=st.session_state.brush_log,  # 過去の指示をすべて渡す
                )
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
                    f1 = ex.submit(run_judge_claude, new_results)
                    f2 = ex.submit(run_judge_chatgpt, new_results)
                    new_judge_claude  = f1.result()
                    new_judge_chatgpt = f2.result()
            st.session_state.results       = new_results
            st.session_state.judge_claude  = new_judge_claude
            st.session_state.judge_chatgpt = new_judge_chatgpt
            st.session_state.brush_log.append(brush_input.strip())
            st.rerun()
        else:
            st.warning("指示を入力してください。")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # ── ② ランキング ──
    if st.session_state.judge_claude or st.session_state.judge_chatgpt:
        j_col1, j_col2 = st.columns(2, gap="medium")

        with j_col1:
            formatted_judge = format_judge(st.session_state.judge_claude, "#a78bfa")
            st.markdown(f"""
<div class="judge-section judge-section-claude">
  <div class="judge-header judge-header-claude">⚖️ &nbsp;Claude による親和性ランキング</div>
  <div class="judge-body">{formatted_judge}</div>
</div>""", unsafe_allow_html=True)

        with j_col2:
            formatted_judge = format_judge(st.session_state.judge_chatgpt, "#34d399")
            st.markdown(f"""
<div class="judge-section judge-section-chatgpt">
  <div class="judge-header judge-header-chatgpt">⚖️ &nbsp;ChatGPT による親和性ランキング</div>
  <div class="judge-body">{formatted_judge}</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── ③ 各AIのネタカード（2行×2列） ──
    def render_card(name):
        if name not in st.session_state.results:
            return
        data      = st.session_state.results[name]
        meta      = AGENT_META[name]
        color     = meta["color"]
        glow      = meta["glow"]
        formatted = format_content(data["content"])
        angle     = html_module.escape(data["angle"])
        st.markdown(f"""
<div class="idea-card" style="box-shadow:0 0 40px rgba({glow},0.08),0 8px 32px rgba(0,0,0,0.5);">
  <div class="card-glow-bar" style="background:linear-gradient(90deg,{color},transparent);"></div>
  <div class="card-header-row">
    <span class="card-agent-name" style="color:{color};">{name}</span>
    <span class="card-angle-tag">{angle}</span>
  </div>
  <div class="card-content">{formatted}</div>
</div>""", unsafe_allow_html=True)

    row1_L, row1_R = st.columns(2, gap="medium")
    with row1_L: render_card("Claude")
    with row1_R: render_card("ChatGPT")

    row2_L, row2_R = st.columns(2, gap="medium")
    with row2_L: render_card("Gemini")
    with row2_R: render_card("Grok")

else:
    st.markdown(
        '<div class="empty-state">「ランダムでネタを生成」を押してスタート</div>',
        unsafe_allow_html=True,
    )
