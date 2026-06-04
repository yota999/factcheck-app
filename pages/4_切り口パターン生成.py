import html as html_module
import concurrent.futures
import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

# ──────────────────────────────────────────────────────────────
# 各AIの担当フォーカス（視点の多様性を出すため）
# ──────────────────────────────────────────────────────────────
AGENT_ORDER = ["Claude", "ChatGPT", "Gemini", "Grok"]

AGENT_META = {
    "Claude":  {"color": "#a78bfa", "glow": "167, 139, 250"},
    "ChatGPT": {"color": "#34d399", "glow": "52, 211, 153"},
    "Gemini":  {"color": "#60a5fa", "glow": "96, 165, 250"},
    "Grok":    {"color": "#fbbf24", "glow": "251, 191, 36"},
}

AGENT_FOCUS = {
    "Claude":  "メカニズム・科学的根拠・生理学的理論の切り口を中心に",
    "ChatGPT": "ターゲット層の具体的な悩み・状況・ライフスタイルの切り口を中心に",
    "Gemini":  "比較対象・否定する対象・対比構造の切り口を中心に",
    "Grok":    "事例・数値・体験談・逆説・意外性の切り口を中心に",
}

# ──────────────────────────────────────────────────────────────
# システムプロンプト
# ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """あなたは動画コンテンツの企画・構成の専門家です。
与えられた動画テーマに対して、同じテーマを「別の切り口」で展開するパターンを4つ提案してください。

【切り口の種類（参考）】
・否定する対象を変える（別の運動・食事・習慣を否定する）
・メカニズムの説明角度を変える（別の生理学・解剖学的理論から説明する）
・ターゲット層の具体的な悩みを変える（産後・座り仕事・年代・体型 など）
・比較対象を変える（別のトレンドや人気メソッドを否定する）
・事例・数値・体験談の切り口を変える（具体的なクライアント事例や数値を前面に）
・意外な原因・逆説的な切り口（常識の逆を突く）
・時間軸を変える（短期・長期・年齢段階別）

【出力形式】（必ずこの形式で4つ出すこと）

パターンA：[切り口の名前（15文字以内）]
何を変えるか：[1行で端的に]
内容：[動画の構成や訴求ポイントが具体的にわかる2〜3文]

パターンB：[切り口の名前]
何を変えるか：[同上]
内容：[同上]

（パターンC・Dも同様）

【ルール】
・日本語で出力
・各パターンは独立した切り口であること（似たものにならないよう）
・元のテーマの本質（何かを否定する・意外な真実を教える等の構造）は維持
・視聴者が「見たい！」と思えるような具体的な表現で

【出力禁止】
・高齢者（60代以上）向けの内容
・アスリート・競技者・スポーツ選手向けの内容
・特定の疾患・障害を持つ人向けの内容
→ あくまで一般的な30代〜50代の日本人女性が対象"""

# ──────────────────────────────────────────────────────────────
# 各AI生成関数
# ──────────────────────────────────────────────────────────────
def gen_claude(theme: str, focus: str) -> str:
    from anthropic import Anthropic
    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"【担当フォーカス】{focus}\n\n【テーマ】{theme}"}],
    )
    return msg.content[0].text


def gen_chatgpt(theme: str, focus: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    res = client.chat.completions.create(
        model="gpt-4o", max_tokens=1200,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"【担当フォーカス】{focus}\n\n【テーマ】{theme}"},
        ],
    )
    return res.choices[0].message.content


def gen_gemini(theme: str, focus: str) -> str:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY", ""))
    res = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=SYSTEM_PROMPT + f"\n\n【担当フォーカス】{focus}\n\n【テーマ】{theme}",
        config=types.GenerateContentConfig(
            max_output_tokens=1200,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    return res.text


def gen_grok(theme: str, focus: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("XAI_API_KEY", ""), base_url="https://api.x.ai/v1")
    res = client.chat.completions.create(
        model="grok-3", max_tokens=1200,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"【担当フォーカス】{focus}\n\n【テーマ】{theme}"},
        ],
    )
    return res.choices[0].message.content


GEN_FUNCS = {
    "Claude": gen_claude, "ChatGPT": gen_chatgpt,
    "Gemini": gen_gemini, "Grok":    gen_grok,
}

# ──────────────────────────────────────────────────────────────
# 全AI並列実行
# ──────────────────────────────────────────────────────────────
def run_all(theme: str) -> dict:
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futures = {
            ex.submit(GEN_FUNCS[name], theme, AGENT_FOCUS[name]): name
            for name in AGENT_ORDER
        }
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                content = future.result()
            except Exception as e:
                content = f"⚠️ エラー\n{e}"
            results[name] = content
    return results

# ──────────────────────────────────────────────────────────────
# 出力をHTMLに整形
# ──────────────────────────────────────────────────────────────
def format_patterns(text: str, color: str) -> str:
    lines = [l.strip() for l in text.splitlines()]
    html  = ""
    i     = 0
    while i < len(lines):
        line = lines[i]
        if not line:
            i += 1
            continue

        # パターン行（パターンA: や パターンA： で始まる）
        if line.startswith("パターン") and ("：" in line or ":" in line):
            sep   = "：" if "：" in line else ":"
            label = line.split(sep)[0].strip()   # 例：パターンA
            title = line.split(sep, 1)[1].strip() # 例：切り口の名前
            html += f"""
<div style="margin-bottom:20px;">
  <div style="font-size:11px; font-weight:700; letter-spacing:0.1em;
       color:{color}; margin-bottom:6px; text-transform:uppercase;">
    {html_module.escape(label)}
  </div>
  <div style="font-size:14px; font-weight:600; color:#e2e8f0; margin-bottom:8px;">
    {html_module.escape(title)}
  </div>"""
            i += 1

        # 何を変えるか行
        elif line.startswith("何を変えるか"):
            val = line.split("：")[-1].split(":")[-1].strip()
            html += f"""
  <div style="font-size:12px; color:#6366f1; background:rgba(99,102,241,0.1);
       border-radius:6px; padding:5px 10px; margin-bottom:6px; display:inline-block;">
    🔄 {html_module.escape(val)}
  </div>"""
            i += 1

        # 内容行
        elif line.startswith("内容"):
            val = line.split("：")[-1].split(":")[-1].strip()
            # 次の行も内容の続きかもしれないので連結
            i += 1
            while i < len(lines) and lines[i] and not lines[i].startswith("パターン") and not lines[i].startswith("何を変えるか"):
                val += " " + lines[i].strip()
                i += 1
            html += f"""
  <div style="font-size:13px; color:#e2e8f0; line-height:1.75;
       border-left:2px solid rgba(255,255,255,0.08);
       padding-left:12px; margin-top:4px;">
    {html_module.escape(val)}
  </div>
</div>
<div style="height:1px; background:rgba(255,255,255,0.05); margin-bottom:16px;"></div>"""

        else:
            i += 1

    return html

# ──────────────────────────────────────────────────────────────
# Streamlit UI
# ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="切り口パターン生成", page_icon="🔀", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
* { font-family: 'Inter', sans-serif !important; }

[data-testid="stAppViewContainer"] {
    background: radial-gradient(ellipse at 80% 0%, #0a1520 0%, #06060f 40%, #080818 100%);
    min-height: 100vh;
}
[data-testid="stHeader"]  { background: transparent !important; }
[data-testid="stSidebar"] { background: #07070f !important; }
[data-testid="stSidebarContent"] { background: #07070f !important; }

.block-container { padding-top: 2rem !important; max-width: 1400px; }

.page-header { text-align: center; padding: 48px 0 16px; }
.page-title {
    font-size: 32px; font-weight: 700; letter-spacing: -0.5px;
    background: linear-gradient(135deg, #e2d9f3 0%, #60a5fa 40%, #34d399 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; margin-bottom: 8px;
}
.page-subtitle { font-size: 13px; color: #94a3b8; letter-spacing: 0.05em; }
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #1e1e38, transparent);
    margin: 24px 0;
}
.section-label {
    font-size: 11px; font-weight: 600; letter-spacing: 0.12em;
    text-transform: uppercase; color: #94a3b8; margin-bottom: 10px;
}
.pattern-card {
    position: relative; border-radius: 20px; padding: 28px 30px;
    margin-bottom: 16px;
    background: linear-gradient(145deg, #0c0c1e 0%, #0f0f24 100%);
    border: 1px solid rgba(255,255,255,0.04);
    box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    transition: transform 0.2s ease;
}
.pattern-card:hover { transform: translateY(-2px); }
.card-glow-bar {
    position: absolute; top: 0; left: 0; right: 0;
    height: 2px; border-radius: 20px 20px 0 0;
}
.card-agent-name {
    font-size: 11px; font-weight: 700;
    letter-spacing: 0.15em; text-transform: uppercase;
    margin-bottom: 6px;
}
.card-focus-tag {
    font-size: 10px; color: #374151;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 20px; padding: 3px 10px;
    margin-bottom: 18px; display: inline-block;
}
.card-content-area {
    border-top: 1px solid rgba(255,255,255,0.06);
    padding-top: 16px;
}
div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #1d4ed8, #0891b2) !important;
    color: white !important; border: none !important;
    border-radius: 12px !important; padding: 12px 32px !important;
    font-size: 14px !important; font-weight: 600 !important;
    letter-spacing: 0.03em !important;
    box-shadow: 0 0 24px rgba(29,78,216,0.4), 0 4px 16px rgba(0,0,0,0.4) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    box-shadow: 0 0 36px rgba(29,78,216,0.6), 0 4px 24px rgba(0,0,0,0.5) !important;
    transform: translateY(-1px) !important;
}
div[data-testid="stButton"] > button[kind="secondary"] {
    background: rgba(255,255,255,0.04) !important;
    color: #6b7280 !important; border: 1px solid #1f2937 !important;
    border-radius: 8px !important; font-size: 12px !important;
}
[data-testid="stTextInput"] input {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid #1e1e38 !important; border-radius: 12px !important;
    color: #e2e8f0 !important; font-size: 14px !important;
    padding: 12px 16px !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: #1d4ed8 !important;
    box-shadow: 0 0 0 3px rgba(29,78,216,0.15) !important;
}
[data-testid="stTextInput"] input::placeholder { color: transparent !important; }
.theme-badge {
    display: inline-block; font-size: 13px; font-weight: 600;
    color: #e2e8f0; background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; padding: 8px 16px; margin-bottom: 20px;
}
.empty-state {
    text-align: center; padding: 80px 0;
    color: #4b5563; font-size: 14px; letter-spacing: 0.05em;
}
h1, h2, h3, p, label { color: #e2e8f0 !important; }
[data-testid="stMarkdownContainer"] p { color: #94a3b8 !important; }
[data-testid="stMarkdownContainer"] { color: #e2e8f0 !important; }
span, div { color: inherit; }
</style>
""", unsafe_allow_html=True)

# ── セッション初期化 ──
for key, default in [("pattern_results", {}), ("current_theme", "")]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── ヘッダー ──
st.markdown("""
<div class="page-header">
  <div class="page-title">切り口パターン生成</div>
  <div class="page-subtitle">4 AI AGENTS · ANGLE VARIATIONS · SAME THEME · DIFFERENT PERSPECTIVES</div>
</div>
""", unsafe_allow_html=True)
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ── テーマ入力 ──
st.markdown('<div class="section-label">動画テーマを入力</div>', unsafe_allow_html=True)
col_inp, col_btn = st.columns([5, 1])
with col_inp:
    theme_input = st.text_input(
        "theme",
        placeholder="",
        label_visibility="collapsed",
    )
with col_btn:
    gen_clicked = st.button("🔀 生成", type="primary", use_container_width=True)

if gen_clicked:
    if theme_input.strip():
        with st.spinner("4つのAIが異なる視点から切り口を考え中..."):
            st.session_state.pattern_results = run_all(theme_input.strip())
            st.session_state.current_theme   = theme_input.strip()
    else:
        st.warning("テーマを入力してください。")

# ── リセット ──
if st.session_state.current_theme:
    st.markdown(f'<div class="theme-badge">🎯 &nbsp;{html_module.escape(st.session_state.current_theme)}</div>', unsafe_allow_html=True)
    col_r, col_sp = st.columns([1, 5])
    with col_r:
        if st.button("リセット", type="secondary", use_container_width=True):
            st.session_state.pattern_results = {}
            st.session_state.current_theme   = ""
            st.rerun()

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ── 結果表示 ──
if st.session_state.pattern_results:

    def render_pattern_card(name):
        if name not in st.session_state.pattern_results:
            return
        content = st.session_state.pattern_results[name]
        meta    = AGENT_META[name]
        color   = meta["color"]
        glow    = meta["glow"]
        focus   = html_module.escape(AGENT_FOCUS[name])
        formatted = format_patterns(content, color)

        st.markdown(f"""
<div class="pattern-card" style="box-shadow:0 0 40px rgba({glow},0.08),0 8px 32px rgba(0,0,0,0.5);">
  <div class="card-glow-bar" style="background:linear-gradient(90deg,{color},transparent);"></div>
  <div class="card-agent-name" style="color:{color};">{name}</div>
  <div class="card-focus-tag">{focus}</div>
  <div class="card-content-area">{formatted}</div>
</div>""", unsafe_allow_html=True)

    row1_L, row1_R = st.columns(2, gap="medium")
    with row1_L: render_pattern_card("Claude")
    with row1_R: render_pattern_card("ChatGPT")

    row2_L, row2_R = st.columns(2, gap="medium")
    with row2_L: render_pattern_card("Gemini")
    with row2_R: render_pattern_card("Grok")

else:
    st.markdown(
        '<div class="empty-state">テーマを入力して「🔀 生成」を押してください</div>',
        unsafe_allow_html=True,
    )
