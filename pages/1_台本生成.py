import os
import sys
import queue
import threading
import time
import datetime
from io import StringIO

import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=True)

try:
    for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "SERPER_API_KEY",
                "GOOGLE_API_KEY", "XAI_API_KEY"]:
        if key in st.secrets and not os.getenv(key):
            os.environ[key] = st.secrets[key]
except Exception:
    pass

st.set_page_config(
    page_title="台本生成システム",
    page_icon="📝",
    layout="wide",
)

# ─── CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ═══ Google Fonts 読み込み ═══ */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;600;700;800;900&display=swap');

/* ═══ ベース ═══ */
.main {
    background: linear-gradient(180deg, #F8FAFF 0%, #EEF1F8 40%, #F0F2F6 100%);
    font-family: 'Noto Sans JP', sans-serif;
}
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #FAFBFE 0%, #F3F4FA 100%);
    border-right: 1px solid #E5E7EB;
}
section[data-testid="stSidebar"] .stMarkdown {
    font-size: 0.88rem;
}

/* ═══ ページヘッダー ═══ */
.page-header {
    background: linear-gradient(135deg, #1E1B4B 0%, #312E81 30%, #4338CA 60%, #6D28D9 100%);
    border-radius: 20px;
    padding: 32px 36px 28px;
    color: white;
    margin-bottom: 28px;
    box-shadow: 0 8px 32px rgba(79,70,229,.22), 0 2px 8px rgba(0,0,0,.06);
    position: relative;
    overflow: hidden;
}
.page-header::before {
    content: '';
    position: absolute; left: -60px; bottom: -60px;
    width: 200px; height: 200px;
    background: rgba(255,255,255,.04);
    border-radius: 50%;
}
.page-header::after {
    content: '';
    position: absolute; right: -40px; top: -40px;
    width: 180px; height: 180px;
    background: rgba(255,255,255,.06);
    border-radius: 50%;
}
.page-header h1 {
    margin: 0; font-size: 1.9rem; color: white;
    letter-spacing: -.03em; font-weight: 800;
    text-shadow: 0 2px 4px rgba(0,0,0,.15);
}
.page-header p {
    margin: 8px 0 0; opacity: 0.78; font-size: 0.88rem;
    line-height: 1.6; letter-spacing: .01em;
}

/* ═══ ステッププログレス ═══ */
.steps-wrap {
    display: flex; align-items: center; justify-content: center;
    background: white;
    border-radius: 16px;
    padding: 20px 32px;
    box-shadow: 0 2px 16px rgba(0,0,0,.05), 0 1px 3px rgba(0,0,0,.03);
    margin-bottom: 28px;
    gap: 0;
    border: 1px solid rgba(229,231,235,.6);
}
.step-item {
    display: flex; flex-direction: column; align-items: center;
    flex: 1; position: relative; z-index: 1;
}
.step-num {
    width: 38px; height: 38px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.85rem; font-weight: 700;
    margin-bottom: 8px;
    transition: all .3s cubic-bezier(.4,0,.2,1);
}
.step-label {
    font-size: 0.73rem; text-align: center;
    white-space: nowrap; letter-spacing: .02em;
    transition: all .3s;
}
.step-done .step-num {
    background: linear-gradient(135deg, #059669, #10B981);
    color: white;
    box-shadow: 0 3px 12px rgba(5,150,105,.3);
}
.step-done .step-label { color: #059669; font-weight: 600; }
.step-active .step-num {
    background: linear-gradient(135deg, #4338CA, #6D28D9);
    color: white;
    box-shadow: 0 0 0 4px #C7D2FE, 0 3px 12px rgba(79,70,229,.3);
    animation: pulse-ring 2s ease-out infinite;
}
@keyframes pulse-ring {
    0% { box-shadow: 0 0 0 4px #C7D2FE, 0 3px 12px rgba(79,70,229,.3); }
    50% { box-shadow: 0 0 0 6px #DDD6FE, 0 3px 16px rgba(79,70,229,.2); }
    100% { box-shadow: 0 0 0 4px #C7D2FE, 0 3px 12px rgba(79,70,229,.3); }
}
.step-active .step-label { color: #4338CA; font-weight: 700; }
.step-pending .step-num {
    background: #F9FAFB; color: #9CA3AF;
    border: 2px solid #E5E7EB;
}
.step-pending .step-label { color: #9CA3AF; }
.step-connector {
    height: 3px; background: #E5E7EB;
    flex: 0 0 36px; margin-bottom: 24px;
    border-radius: 2px; transition: background .3s;
}
.step-connector.done {
    background: linear-gradient(90deg, #059669, #10B981);
    box-shadow: 0 1px 4px rgba(5,150,105,.2);
}

/* ═══ セクションヘッダー ═══ */
.section-header {
    background: linear-gradient(90deg, #EEF2FF 0%, #F5F3FF 60%, transparent 100%);
    border-left: 4px solid #4F46E5;
    padding: 12px 18px;
    border-radius: 0 10px 10px 0;
    font-weight: 700; font-size: 1.02rem;
    margin: 24px 0 16px;
    color: #1E1B4B;
    letter-spacing: -.01em;
}

/* ═══ 統計カード ═══ */
.stat-box {
    background: white;
    border-radius: 14px;
    padding: 20px 14px;
    text-align: center;
    border: 1px solid #E5E7EB;
    box-shadow: 0 2px 8px rgba(0,0,0,.03);
    transition: all .2s cubic-bezier(.4,0,.2,1);
}
.stat-box:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(79,70,229,.1);
    border-color: #C7D2FE;
}
.stat-num {
    font-size: 2.2rem; font-weight: 800;
    background: linear-gradient(135deg, #4338CA, #6D28D9);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; line-height: 1.2;
}
.stat-lbl {
    font-size: 0.74rem; color: #6366F1;
    margin-top: 4px; font-weight: 500;
    letter-spacing: .02em;
}

/* ═══ インフォカード ═══ */
.info-card {
    background: white;
    border: 1px solid #E5E7EB;
    border-radius: 14px;
    padding: 20px 22px;
    box-shadow: 0 2px 8px rgba(0,0,0,.03);
    transition: all .2s;
}
.info-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.06); }
.info-card-label {
    font-size: 0.73rem; color: #9CA3AF;
    font-weight: 600; text-transform: uppercase;
    letter-spacing: .06em; margin-bottom: 12px;
}
.info-card-row {
    display: flex; align-items: center; gap: 8px;
    padding: 6px 0; font-size: 0.88rem; color: #374151;
}
.info-card-row .icon {
    width: 28px; height: 28px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.9rem; flex-shrink: 0;
}

/* ═══ タイプカード ═══ */
.type-card {
    border: 2px solid #E5E7EB;
    border-radius: 18px;
    padding: 28px 20px 22px;
    text-align: center;
    background: white;
    transition: all .25s cubic-bezier(.4,0,.2,1);
    cursor: pointer;
    position: relative;
    overflow: hidden;
}
.type-card::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 4px;
    background: linear-gradient(90deg, #4338CA, #7C3AED);
    opacity: 0; transition: opacity .25s;
}
.type-card:hover {
    border-color: #A5B4FC;
    box-shadow: 0 8px 28px rgba(79,70,229,.12);
    transform: translateY(-2px);
}
.type-card:hover::before { opacity: 1; }
.type-card.selected {
    border-color: #4F46E5;
    background: linear-gradient(180deg, #FAFAFE 0%, #F5F3FF 100%);
    box-shadow: 0 4px 20px rgba(79,70,229,.15);
}
.type-card.selected::before { opacity: 1; }
.type-card-icon {
    font-size: 2.8rem; margin-bottom: 12px;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,.1));
}
.type-card-title {
    font-size: 1.1rem; font-weight: 700;
    color: #1E1B4B; margin-bottom: 6px;
}
.type-card-desc {
    font-size: 0.8rem; color: #6B7280;
    line-height: 1.5;
}
.type-card-badge {
    display: inline-block; margin-top: 10px;
    background: #EEF2FF; color: #4338CA;
    font-size: 0.72rem; font-weight: 600;
    padding: 4px 12px; border-radius: 20px;
}

/* ═══ ヒントボックス ═══ */
.hint-box {
    background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%);
    border: 1px solid #FDE68A;
    border-radius: 12px;
    padding: 14px 18px;
    font-size: 0.84rem;
    color: #92400E;
    line-height: 1.6;
    display: flex; align-items: flex-start; gap: 10px;
}
.hint-box .hint-icon { font-size: 1.1rem; flex-shrink: 0; margin-top: 1px; }

/* ═══ ドロップダウン全文表示 ═══ */
/* メニューコンテナ */
[data-baseweb="popover"] > div,
[data-baseweb="menu"],
[data-baseweb="menu"] ul,
[data-baseweb="menu"] [role="listbox"] {
    overflow: visible !important;
    height: auto !important;
    max-height: 480px !important;
}
/* 各リストアイテム */
[data-baseweb="menu"] li,
[data-baseweb="menu"] [role="option"] {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
    height: auto !important;
    min-height: 44px !important;
    padding: 12px 18px !important;
    line-height: 1.65 !important;
    border-bottom: none !important;
    transition: background .1s;
    font-size: 0.9rem !important;
    word-break: break-all;
    word-wrap: break-word;
}
/* アイテム内のテキストspan */
[data-baseweb="menu"] li span,
[data-baseweb="menu"] li div,
[data-baseweb="menu"] [role="option"] span {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
    max-width: 100% !important;
    display: inline !important;
}
[data-baseweb="menu"] li:nth-child(odd) {
    background: #F5F3FF !important;
}
[data-baseweb="menu"] li:nth-child(even) {
    background: white !important;
}
[data-baseweb="menu"] li:hover {
    background: #EEF2FF !important;
    box-shadow: inset 3px 0 0 #4F46E5;
}

/* ═══ マルチセレクト選択済みタグ全文表示 ═══ */
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
    max-width: 100% !important;
    white-space: normal !important;
    height: auto !important;
    padding: 4px 8px !important;
    line-height: 1.5 !important;
    border-radius: 6px !important;
}
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] span,
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] div {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
    max-width: 100% !important;
}
/* マルチセレクトの入力ボックス */
div[data-testid="stMultiSelect"] > div {
    height: auto !important;
    min-height: 44px !important;
}
div[data-testid="stMultiSelect"] > div > div {
    flex-wrap: wrap !important;
    height: auto !important;
}

/* ═══ ラジオボタンを候補カード風に ═══ */
div[data-testid="stRadio"] > div[role="radiogroup"] > label {
    background: white;
    border: 1.5px solid #E5E7EB;
    border-radius: 12px;
    padding: 14px 18px !important;
    margin-bottom: 8px;
    transition: all .2s cubic-bezier(.4,0,.2,1);
    line-height: 1.65 !important;
    cursor: pointer;
    box-shadow: 0 1px 3px rgba(0,0,0,.02);
}
div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {
    border-color: #A5B4FC;
    background: #FAFAFF;
    box-shadow: 0 3px 12px rgba(79,70,229,.08);
    transform: translateX(2px);
}
div[data-testid="stRadio"] > div[role="radiogroup"] > label[data-checked="true"],
div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {
    border-color: #4F46E5;
    background: linear-gradient(135deg, #EEF2FF, #F5F3FF);
    box-shadow: 0 3px 16px rgba(79,70,229,.12);
    border-left: 4px solid #4F46E5;
}

/* ═══ タブ ═══ */
button[data-baseweb="tab"] {
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 12px 24px !important;
    border-radius: 10px 10px 0 0 !important;
    transition: all .15s !important;
}
button[data-baseweb="tab"]:hover {
    background: #F5F3FF !important;
}
div[data-baseweb="tab-highlight"] {
    background-color: #4F46E5 !important;
    height: 3px !important;
    border-radius: 3px 3px 0 0 !important;
}

/* ═══ ボタン ═══ */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4338CA 0%, #6D28D9 100%) !important;
    border: none !important;
    box-shadow: 0 4px 16px rgba(79,70,229,.25) !important;
    font-weight: 600 !important;
    letter-spacing: .02em;
    transition: all .2s cubic-bezier(.4,0,.2,1) !important;
    border-radius: 10px !important;
    padding: 10px 24px !important;
    color: white !important;
}
.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span {
    color: white !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 24px rgba(79,70,229,.35) !important;
    transform: translateY(-2px) !important;
}
.stButton > button[kind="primary"]:active {
    transform: translateY(0) !important;
    box-shadow: 0 2px 8px rgba(79,70,229,.2) !important;
}
.stButton > button[kind="secondary"] {
    border: 1.5px solid #D1D5DB !important;
    font-weight: 500 !important;
    transition: all .2s !important;
    border-radius: 10px !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #4F46E5 !important;
    color: #4F46E5 !important;
    background: #EEF2FF !important;
    transform: translateY(-1px) !important;
}

/* ═══ テキストエリア ═══ */
div[data-testid="stTextArea"] textarea {
    border-radius: 12px !important;
    border: 1.5px solid #D1D5DB !important;
    font-size: 0.9rem !important;
    line-height: 1.7 !important;
    padding: 14px 16px !important;
    transition: all .2s !important;
    background: #FAFBFC !important;
}
div[data-testid="stTextArea"] textarea:focus {
    border-color: #4F46E5 !important;
    box-shadow: 0 0 0 3px rgba(79,70,229,.1) !important;
    background: white !important;
}

/* ═══ エクスパンダ ═══ */
details[data-testid="stExpander"] {
    border: 1.5px solid #E5E7EB !important;
    border-radius: 12px !important;
    background: white;
    box-shadow: 0 1px 4px rgba(0,0,0,.02);
    transition: all .15s;
}
details[data-testid="stExpander"]:hover {
    border-color: #C7D2FE !important;
}
details[data-testid="stExpander"] summary {
    font-weight: 600;
    font-size: 0.88rem;
    padding: 14px 18px !important;
}

/* ═══ マルチセレクト ═══ */
div[data-testid="stMultiSelect"] > div > div {
    border-radius: 12px !important;
    border: 1.5px solid #D1D5DB !important;
    transition: border-color .15s;
}
div[data-testid="stMultiSelect"] > div > div:focus-within {
    border-color: #4F46E5 !important;
    box-shadow: 0 0 0 3px rgba(79,70,229,.08) !important;
}

/* ═══ チェックボックス（アイデア一覧）ラベル折り返し ═══ */
div[data-testid="stCheckbox"] label {
    white-space: normal !important;
    overflow: visible !important;
    line-height: 1.7 !important;
    font-size: 0.9rem !important;
    align-items: flex-start !important;
}
div[data-testid="stCheckbox"] label p {
    white-space: normal !important;
    word-break: break-word !important;
}

/* ═══ divider ═══ */
hr { border-color: #E5E7EB !important; margin: 24px 0 !important; }

/* ═══ ダウンロードボタン ═══ */
.stDownloadButton > button {
    border-radius: 10px !important;
    border: 1.5px solid #D1D5DB !important;
    font-weight: 500 !important;
    transition: all .2s !important;
}
.stDownloadButton > button:hover {
    border-color: #4F46E5 !important;
    background: #EEF2FF !important;
    transform: translateY(-1px) !important;
}

/* ═══ FC結果サマリーカード ═══ */
.fc-card {
    text-align: center;
    padding: 16px 10px;
    border-radius: 14px;
    border: 2px solid;
    transition: all .2s;
    position: relative;
    overflow: hidden;
}
.fc-card::after {
    content: '';
    position: absolute; bottom: 0; left: 0; right: 0;
    height: 3px;
}
.fc-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0,0,0,.08);
}
.fc-card .model-name {
    font-size: 0.76rem; font-weight: 700;
    margin-bottom: 8px; letter-spacing: .01em;
}
.fc-card .verdict { font-size: 1.8rem; margin: 4px 0; }
.fc-card .verdict-label {
    font-size: 0.72rem; font-weight: 600;
    border-radius: 6px; padding: 3px 10px;
    display: inline-block; margin-top: 4px;
}

/* ═══ 評価カード ═══ */
.rating-card {
    border-radius: 16px;
    padding: 24px 28px;
    border: 1px solid;
    transition: all .2s;
}
.rating-card:hover {
    transform: translateY(-1px);
}

/* ═══ プログレスバーカスタマイズ ═══ */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #4338CA, #6D28D9, #7C3AED) !important;
    border-radius: 8px !important;
}

/* ═══ スクロールバー ═══ */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: #C7D2FE; border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover { background: #A5B4FC; }

/* ═══ フッター ═══ */
.app-footer {
    background: linear-gradient(135deg, #1E1B4B 0%, #312E81 100%);
    border-radius: 14px;
    padding: 16px 24px;
    color: white;
    text-align: center;
    margin-top: 32px;
    font-size: 0.78rem;
    opacity: 0.9;
}
.app-footer a { color: #C7D2FE; text-decoration: none; }

/* ═══ アニメーション ═══ */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
}
.animate-in { animation: fadeInUp .4s ease-out; }
</style>
""", unsafe_allow_html=True)


# ─── Session State 初期化 ─────────────────────────────────────────────
def _init():
    defaults = {
        "sg_step": 0,
        "sg_script_type": "youtube",
        "sg_themes": [],
        "sg_selected_themes": [],
        "sg_ideas": [],
        "sg_selected_ideas": [],
        "sg_draft": "",
        "sg_edited_draft": "",
        "sg_final_result": "",
        "sg_titles": "",
        "sg_current_angle": ("science", "科学・データ根拠型"),
        "sg_current_ai": ("anthropic/claude-sonnet-4-6", "Claude Sonnet 4.6"),
        "sg_saved": False,
        "sg_rating_mode": None,
        "sg_learned_elements": [],
        "sg_learned_pattern": "",
        # セクションビルダー
        "sg_section_mode": False,
        "sg_sections": [],
        # ファクトチェック
        "sg_fc_results": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()


def reset_all():
    for k in list(st.session_state.keys()):
        if k.startswith("sg_"):
            del st.session_state[k]
    _init()


# ─── ページヘッダー ───────────────────────────────────────────────────
st.markdown("""
<div class="page-header animate-in">
  <h1>📝 台本生成システム</h1>
  <p>AI マルチエージェントが トレンド収集 → テーマ提案 → アイデア → 台本生成 → ファクトチェック まで一気通貫で実行</p>
</div>
""", unsafe_allow_html=True)


# ─── ステッププログレス ───────────────────────────────────────────────
STEP_LABELS = ["タイプ選択", "テーマ選択", "アイデア選択", "台本作成", "FC・完成"]

def render_steps():
    cur = st.session_state.sg_step
    parts = []
    for i, label in enumerate(STEP_LABELS):
        if i < cur:
            cls = "step-done"
            num_html = "✓"
        elif i == cur:
            cls = "step-active"
            num_html = str(i + 1)
        else:
            cls = "step-pending"
            num_html = str(i + 1)
        parts.append(
            f'<div class="step-item {cls}">'
            f'<div class="step-num">{num_html}</div>'
            f'<div class="step-label">{label}</div>'
            f'</div>'
        )
        if i < len(STEP_LABELS) - 1:
            conn_cls = "done" if i < cur else ""
            parts.append(f'<div class="step-connector {conn_cls}"></div>')
    st.markdown(
        f'<div class="steps-wrap animate-in">{"".join(parts)}</div>',
        unsafe_allow_html=True,
    )

render_steps()

step = st.session_state.sg_step


# ════════════════════════════════════════════════════════════════════
# Step 0: タイプ選択
# ════════════════════════════════════════════════════════════════════
if step == 0:
    st.markdown('<div class="section-header">Step 1 ／ 台本のタイプを選択</div>', unsafe_allow_html=True)

    col_yt, col_rl = st.columns(2)
    current_type = st.session_state.sg_script_type

    with col_yt:
        yt_cls = "selected" if current_type == "youtube" else ""
        st.markdown(f'''<div class="type-card {yt_cls}">
<div class="type-card-icon">📺</div>
<div class="type-card-title">YouTube 台本</div>
<div class="type-card-desc">長尺動画向けのしっかりした構成<br>解説・教育系コンテンツに最適</div>
<div class="type-card-badge">4,500〜5,000 文字</div>
</div>''', unsafe_allow_html=True)
        if st.button("📺 YouTube を選択", use_container_width=True,
                     type="primary" if current_type == "youtube" else "secondary",
                     key="sel_yt"):
            st.session_state.sg_script_type = "youtube"
            st.rerun()

    with col_rl:
        rl_cls = "selected" if current_type == "reel" else ""
        st.markdown(f'''<div class="type-card {rl_cls}">
<div class="type-card-icon">📱</div>
<div class="type-card-title">リール台本</div>
<div class="type-card-desc">ショート動画向けのコンパクトな構成<br>インパクト重視・拡散向け</div>
<div class="type-card-badge">700〜800 文字</div>
</div>''', unsafe_allow_html=True)
        if st.button("📱 リール を選択", use_container_width=True,
                     type="primary" if current_type == "reel" else "secondary",
                     key="sel_rl"):
            st.session_state.sg_script_type = "reel"
            st.rerun()

    script_type = current_type
    st.markdown("<br>", unsafe_allow_html=True)

    # 統計 + AI情報
    col_stats, col_ai = st.columns([3, 2])
    with col_stats:
        try:
            from memory_manager import get_stats, get_next_angle, get_next_ai
            stats = get_stats(script_type)
            angle_key, angle_name = get_next_angle(script_type)
            _, ai_name = get_next_ai(script_type)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f'<div class="stat-box"><div class="stat-num">{stats.get("total_generated",0)}</div><div class="stat-lbl">生成済み</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="stat-box"><div class="stat-num" style="background:linear-gradient(135deg,#059669,#10B981);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">{stats.get("good_count",0)}</div><div class="stat-lbl">👍 好評</div></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="stat-box"><div class="stat-num" style="background:linear-gradient(135deg,#DC2626,#EF4444);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">{stats.get("bad_count",0)}</div><div class="stat-lbl">👎 要改善</div></div>', unsafe_allow_html=True)
        except Exception:
            st.info("まだデータがありません — 使うたびにAIが学習して精度が上がります")
    with col_ai:
        try:
            st.markdown(f'''<div class="info-card">
<div class="info-card-label">次回の生成設定</div>
<div class="info-card-row">
    <div class="icon" style="background:#EEF2FF;color:#4338CA;">🎯</div>
    <div><span style="color:#9CA3AF;font-size:0.78rem;">アングル</span><br><b>{angle_name}</b></div>
</div>
<div class="info-card-row">
    <div class="icon" style="background:#F0FDF4;color:#059669;">🤖</div>
    <div><span style="color:#9CA3AF;font-size:0.78rem;">担当AI</span><br><b>{ai_name}</b></div>
</div>
</div>''', unsafe_allow_html=True)
        except Exception:
            pass

    st.markdown('''<div class="hint-box">
<div class="hint-icon">💡</div>
<div>Serper + YouTube Data API でリアルタイムのトレンドを自動収集し、最新の話題に基づいたテーマを提案します。生成するたびにAIが学習し、あなた好みの台本に近づいていきます。</div>
</div>''', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("テーマを自動生成する →", type="primary", use_container_width=True):
        st.session_state.sg_script_type = script_type
        try:
            from memory_manager import get_used_themes, get_next_angle, get_next_ai, get_rejected_themes
            used_themes = get_used_themes(script_type)
            rejected_themes = get_rejected_themes(script_type)
            angle_key, angle_name = get_next_angle(script_type)
            model_id, model_name = get_next_ai(script_type)
        except Exception:
            used_themes, rejected_themes = [], []
            angle_key, angle_name = "science", "科学・データ根拠型"
            model_id, model_name = "anthropic/claude-sonnet-4-6", "Claude Sonnet 4.6"

        st.session_state.sg_current_angle = (angle_key, angle_name)
        st.session_state.sg_current_ai = (model_id, model_name)

        with st.spinner("Serper + YouTube Data API でトレンドを収集中..."):
            try:
                from script_crew import fetch_all_trends
                trends, video_trends, youtube_trends = fetch_all_trends()
            except Exception:
                trends, video_trends, youtube_trends = [], [], []

        with st.spinner(f"{model_name} でテーマを20個生成中...（アングル：{angle_name}）"):
            try:
                from script_crew import generate_themes
                themes = generate_themes(
                    script_type=script_type,
                    used_themes=used_themes,
                    rejected_themes=rejected_themes,
                    trends=trends,
                    video_trends=video_trends,
                    youtube_trends=youtube_trends,
                    angle_name=angle_name,
                    model=model_id,
                )
                st.session_state.sg_themes = themes
                st.session_state.sg_step = 1
                st.rerun()
            except Exception as e:
                import traceback
                st.error(f"エラーが発生しました: {e}\n\nTraceback (most recent call last):\n{traceback.format_exc()}")


# ════════════════════════════════════════════════════════════════════
# Step 1: テーマ選択
# ════════════════════════════════════════════════════════════════════
elif step == 1:
    angle_name = st.session_state.sg_current_angle[1]
    _, ai_name = st.session_state.sg_current_ai

    st.markdown('<div class="section-header">Step 2 ／ テーマを1〜3個選択</div>', unsafe_allow_html=True)

    st.markdown(f'''<div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;">
<div style="background:#EEF2FF;border-radius:8px;padding:6px 14px;font-size:0.82rem;color:#4338CA;font-weight:600;">🎯 アングル: {angle_name}</div>
<div style="background:#F0FDF4;border-radius:8px;padding:6px 14px;font-size:0.82rem;color:#059669;font-weight:600;">🤖 担当AI: {ai_name}</div>
</div>''', unsafe_allow_html=True)

    themes = st.session_state.sg_themes
    CIRCLE_NUMS_T = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
    import re as _re_theme
    def _strip_num_t(text):
        return _re_theme.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]\s*', '', text)
    def _add_num_t(lst):
        result = []
        for idx, item in enumerate(lst):
            clean = _strip_num_t(item)
            if idx < len(CIRCLE_NUMS_T):
                result.append(f"{CIRCLE_NUMS_T[idx]} {clean}")
            else:
                result.append(clean)
        return result
    display_themes = _add_num_t(themes)

    if not themes:
        st.error("テーマ生成に失敗しました。戻って再試行してください。")
    else:
        # 選択済みテーマ（数字なし）を display_themes（数字あり）から逆引きしてデフォルト設定
        _selected_plain = set(st.session_state.sg_selected_themes or [])
        _default_display = [d for d in display_themes if _strip_num_t(d) in _selected_plain]

        selected = st.multiselect(
            "テーマを1〜3個選択（複数選択可）",
            options=display_themes,
            default=_default_display,
            max_selections=3,
            placeholder="クリックしてテーマを選択...",
        )

        with st.expander("🚫 気に入らないテーマをNG登録する（次回から非表示に）"):
            ng_options = [t for t in display_themes if t not in selected]
            ng_selected = st.multiselect(
                "NG登録するテーマを選択", options=ng_options, default=[],
                key="sg_ng_theme_select", placeholder="気に入らないテーマを選ぶ...",
            )
            if st.button("🚫 NG登録する", key="sg_ng_theme_btn", disabled=not ng_selected):
                try:
                    from memory_manager import add_rejected_themes
                    add_rejected_themes([_strip_num_t(x) for x in ng_selected],
                                        st.session_state.sg_script_type)
                    st.success(f"{len(ng_selected)}件をNG登録しました")
                except Exception as e:
                    st.error(f"保存エラー: {e}")

        with st.expander("✏️ リストにないテーマを直接入力して追加"):
            c1, c2 = st.columns([4, 1])
            with c1:
                custom_theme = st.text_input("カスタムテーマ",
                    placeholder="例：更年期後の筋肉量低下を防ぐ方法",
                    label_visibility="collapsed", key="sg_custom_theme_input")
            with c2:
                if st.button("＋追加", key="sg_add_theme",
                             disabled=not custom_theme.strip() or len(selected) >= 3):
                    new_t = custom_theme.strip()
                    # テーマリストに追加（未登録の場合のみ）
                    if new_t not in st.session_state.sg_themes:
                        st.session_state.sg_themes.append(new_t)
                    # 選択済みに追加（数字なしで保持）
                    current_sel = list(st.session_state.sg_selected_themes or [])
                    if new_t not in current_sel:
                        current_sel.append(new_t)
                    st.session_state.sg_selected_themes = current_sel
                    st.rerun()
            if len(selected) >= 3:
                st.caption("（3個選択済みのため追加できません）")

        st.markdown("<br>", unsafe_allow_html=True)
        col_back, col_regen, col_next = st.columns([1, 1, 2])
        with col_back:
            if st.button("← 戻る"):
                st.session_state.sg_step = 0
                st.rerun()
        with col_regen:
            if st.button("🔄 テーマを再生成"):
                try:
                    from memory_manager import get_used_themes, get_next_angle, get_next_ai, get_rejected_themes
                    used_themes = get_used_themes(st.session_state.sg_script_type)
                    rejected_themes = get_rejected_themes(st.session_state.sg_script_type)
                    angle_key, angle_name = get_next_angle(st.session_state.sg_script_type)
                    model_id, model_name = get_next_ai(st.session_state.sg_script_type)
                except Exception:
                    used_themes, rejected_themes = [], []
                    angle_key, angle_name = "science", "科学・データ根拠型"
                    model_id, model_name = "anthropic/claude-sonnet-4-6", "Claude Sonnet 4.6"

                st.session_state.sg_current_angle = (angle_key, angle_name)
                st.session_state.sg_current_ai = (model_id, model_name)

                with st.spinner(f"{model_name} で再生成中..."):
                    try:
                        from script_crew import fetch_all_trends, generate_themes
                        trends, video_trends, youtube_trends = fetch_all_trends()
                        themes = generate_themes(
                            script_type=st.session_state.sg_script_type,
                            used_themes=used_themes, rejected_themes=rejected_themes,
                            trends=trends, video_trends=video_trends,
                            youtube_trends=youtube_trends, angle_name=angle_name,
                            model=model_id,
                        )
                        st.session_state.sg_themes = themes
                        st.session_state.sg_selected_themes = []
                        st.rerun()
                    except Exception as e:
                        st.error(f"エラー: {e}")
        with col_next:
            if st.button("アイデア20個を生成 →", type="primary", disabled=len(selected) == 0,
                         use_container_width=True):
                # 丸数字を除去して内部データとして保存
                st.session_state.sg_selected_themes = [_strip_num_t(x) for x in selected]
                angle_name = st.session_state.sg_current_angle[1]
                model_id = st.session_state.sg_current_ai[0]
                try:
                    from memory_manager import get_good_elements, get_rejected_ideas
                    good_elements = get_good_elements(st.session_state.sg_script_type)
                    rejected_ideas = get_rejected_ideas(st.session_state.sg_script_type)
                except Exception:
                    good_elements, rejected_ideas = [], []

                with st.spinner("コンテンツアイデアを20個生成中..."):
                    try:
                        from script_crew import generate_ideas
                        ideas = generate_ideas(
                            script_type=st.session_state.sg_script_type,
                            selected_themes=st.session_state.sg_selected_themes,
                            angle_name=angle_name,
                            good_elements=good_elements, rejected_ideas=rejected_ideas,
                            model=model_id,
                        )
                        st.session_state.sg_ideas = ideas
                        st.session_state.sg_step = 2
                        st.rerun()
                    except Exception as e:
                        import traceback
                        st.error(f"エラー:\n{e}\n\n{traceback.format_exc()}")


# ════════════════════════════════════════════════════════════════════
# Step 2: アイデア選択
# ════════════════════════════════════════════════════════════════════
elif step == 2:
    themes_str = " / ".join(st.session_state.sg_selected_themes)
    _, ai_name = st.session_state.sg_current_ai

    st.markdown('<div class="section-header">Step 3 ／ アイデアを3個選択</div>', unsafe_allow_html=True)

    st.markdown(f'''<div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;">
<div style="background:#FEF3C7;border-radius:8px;padding:6px 14px;font-size:0.82rem;color:#92400E;font-weight:600;">📌 テーマ: {themes_str}</div>
<div style="background:#F0FDF4;border-radius:8px;padding:6px 14px;font-size:0.82rem;color:#059669;font-weight:600;">🤖 担当AI: {ai_name}</div>
</div>''', unsafe_allow_html=True)

    ideas = st.session_state.sg_ideas
    # 丸数字プレフィックスを付与（表示用）
    CIRCLE_NUMS = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
    import re as _re_idea
    def _strip_num(text):
        """丸数字プレフィックスを除去して元のテキストに戻す"""
        return _re_idea.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]\s*', '', text)
    def _add_num(idea_list):
        """アイデアに丸数字を付与（既に付いていればスキップ）"""
        result = []
        for idx, idea in enumerate(idea_list):
            clean = _strip_num(idea)
            if idx < len(CIRCLE_NUMS):
                result.append(f"{CIRCLE_NUMS[idx]} {clean}")
            else:
                result.append(clean)
        return result
    display_ideas = _add_num(ideas)

    if not ideas:
        st.error("アイデア生成に失敗しました。戻って再試行してください。")
    else:
        # ── チェックボックス方式でアイデアを表示（全文表示・縞模様・3個まで選択） ──
        current_plain = set(st.session_state.sg_selected_ideas or [])
        new_plain = set()

        n_checked = sum(1 for idea in display_ideas if _strip_num(idea) in current_plain)
        # カスタム追加分も含めてカウント
        custom_checked = sum(1 for x in current_plain if x not in [_strip_num(d) for d in display_ideas])
        total_checked = n_checked + custom_checked

        st.markdown(
            f'<div style="font-size:0.88rem;color:#6B7280;margin-bottom:10px;">'
            f'アイデアを最大3個選択してください ― <b style="color:{"#4F46E5" if total_checked>0 else "#6B7280"}">{total_checked}/3 選択中</b></div>',
            unsafe_allow_html=True,
        )

        for i, idea in enumerate(display_ideas):
            plain = _strip_num(idea)
            is_checked = plain in current_plain
            max_reached = total_checked >= 3 and not is_checked
            bg = "#F5F3FF" if i % 2 == 0 else "#FFFFFF"
            border = "#C4B5FD" if is_checked else "#E5E7EB"
            st.markdown(
                f'<div style="background:{bg};border:1.5px solid {border};border-radius:8px;'
                f'padding:10px 14px;margin-bottom:6px;line-height:1.65;">',
                unsafe_allow_html=True,
            )
            checked = st.checkbox(
                idea,
                value=is_checked,
                key=f"idea_chk_{i}",
                disabled=max_reached,
            )
            st.markdown("</div>", unsafe_allow_html=True)
            if checked:
                new_plain.add(plain)

        # カスタム追加分を保持
        for x in current_plain:
            if x not in [_strip_num(d) for d in display_ideas]:
                new_plain.add(x)

        if new_plain != current_plain:
            st.session_state.sg_selected_ideas = list(new_plain)
            st.rerun()

        # selected_ideas は後続コードとの互換用
        selected_ideas = [d for d in display_ideas if _strip_num(d) in new_plain]
        # カスタム追加分も含める
        for x in new_plain:
            if x not in [_strip_num(d) for d in display_ideas]:
                selected_ideas.append(x)

        total_checked = len(new_plain)

        with st.expander("🚫 気に入らないアイデアをNG登録する（次回から非表示に）"):
            ng_options = [idea for idea in display_ideas if _strip_num(idea) not in new_plain]
            ng_sel_keys = [f"ng_idea_{i}" for i, idea in enumerate(display_ideas)
                           if _strip_num(idea) not in new_plain]
            ng_checked = []
            for idea in ng_options:
                plain = _strip_num(idea)
                if st.checkbox(f"🚫 {idea}", key=f"ng_idea_chk_{plain[:20]}", value=False):
                    ng_checked.append(plain)
            if st.button("🚫 NG登録する", key="sg_ng_idea_btn", disabled=not ng_checked):
                try:
                    from memory_manager import add_rejected_ideas
                    add_rejected_ideas(ng_checked, st.session_state.sg_script_type)
                    st.success(f"{len(ng_checked)}件をNG登録しました")
                except Exception as e:
                    st.error(f"保存エラー: {e}")

        with st.expander("✏️ リストにないアイデアを直接入力して追加"):
            c1, c2 = st.columns([4, 1])
            with c1:
                custom_idea = st.text_input("カスタムアイデア",
                    placeholder="例：夫に言われた一言で決意した体験談",
                    label_visibility="collapsed", key="sg_custom_idea_input")
            with c2:
                add_disabled = not custom_idea.strip() or total_checked >= 3
                if st.button("＋追加", key="sg_add_idea", disabled=add_disabled):
                    new_idea = custom_idea.strip()
                    if new_idea not in st.session_state.sg_ideas:
                        st.session_state.sg_ideas.append(new_idea)
                    current_sel = list(st.session_state.sg_selected_ideas or [])
                    if new_idea not in current_sel:
                        current_sel.append(new_idea)
                    st.session_state.sg_selected_ideas = current_sel
                    st.rerun()
            if total_checked >= 3:
                st.caption("（3個選択済みのため追加できません）")

        st.markdown("<br>", unsafe_allow_html=True)
        col_back, col_regen, col_next = st.columns([1, 1, 2])
        with col_back:
            if st.button("← 戻る"):
                st.session_state.sg_step = 1
                st.rerun()
        with col_regen:
            if st.button("🔄 アイデアを再生成"):
                model_id = st.session_state.sg_current_ai[0]
                angle_name = st.session_state.sg_current_angle[1]
                try:
                    from memory_manager import get_good_elements, get_rejected_ideas
                    good_elements = get_good_elements(st.session_state.sg_script_type)
                    rejected_ideas = get_rejected_ideas(st.session_state.sg_script_type)
                except Exception:
                    good_elements, rejected_ideas = [], []
                with st.spinner("アイデアを再生成中..."):
                    try:
                        from script_crew import generate_ideas
                        new_ideas = generate_ideas(
                            script_type=st.session_state.sg_script_type,
                            selected_themes=st.session_state.sg_selected_themes,
                            angle_name=angle_name, good_elements=good_elements,
                            rejected_ideas=rejected_ideas, model=model_id,
                        )
                        st.session_state.sg_ideas = new_ideas
                        st.session_state.sg_selected_ideas = []
                        st.rerun()
                    except Exception as e:
                        st.error(f"エラー: {e}")
        with col_next:
            if st.button("台本を生成 →", type="primary", disabled=total_checked == 0,
                         use_container_width=True):
                # 丸数字を除去して内部データとして保存
                st.session_state.sg_selected_ideas = list(new_plain)
                model_id = st.session_state.sg_current_ai[0]
                angle_name = st.session_state.sg_current_angle[1]
                script_type = st.session_state.sg_script_type
                char_range = "4500〜5000文字" if script_type == "youtube" else "700〜800文字"

                try:
                    from memory_manager import get_good_elements, get_bad_patterns, get_reference_scripts
                    good_elements = get_good_elements(script_type)
                    bad_patterns = get_bad_patterns(script_type)
                    ref_scripts = get_reference_scripts(script_type)
                except Exception:
                    good_elements, bad_patterns, ref_scripts = [], [], []

                with st.spinner(f"台本を生成中... ({char_range})"):
                    try:
                        from script_crew import generate_draft
                        draft = generate_draft(
                            script_type=script_type,
                            selected_themes=st.session_state.sg_selected_themes,
                            selected_ideas=selected_ideas,
                            good_elements=good_elements, bad_patterns=bad_patterns,
                            ref_scripts=ref_scripts, model=model_id,
                        )
                        st.session_state.sg_draft = draft
                        st.session_state.sg_edited_draft = draft
                        st.session_state.sg_sections = []
                        st.session_state.sg_section_mode = False
                        st.session_state.sg_step = 3
                        st.rerun()
                    except Exception as e:
                        import traceback
                        st.error(f"エラー:\n{e}\n\n{traceback.format_exc()}")


# ════════════════════════════════════════════════════════════════════
# Step 3: 台本作成（テキスト直接編集 ＋ セクションビルダー）
# ════════════════════════════════════════════════════════════════════
elif step == 3:
    _, ai_name = st.session_state.sg_current_ai
    script_type = st.session_state.sg_script_type
    model_id = st.session_state.sg_current_ai[0]
    target_min, target_max = (4500, 5000) if script_type == "youtube" else (700, 800)

    st.markdown('<div class="section-header">Step 4 ／ 台本を確認・調整</div>', unsafe_allow_html=True)

    st.markdown(f'''<div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;">
<div style="background:#F0FDF4;border-radius:8px;padding:6px 14px;font-size:0.82rem;color:#059669;font-weight:600;">🤖 担当AI: {ai_name}</div>
<div style="background:#EEF2FF;border-radius:8px;padding:6px 14px;font-size:0.82rem;color:#4338CA;font-weight:600;">📏 目標: {target_min}〜{target_max}文字</div>
</div>''', unsafe_allow_html=True)

    # ── モード切り替えタブ ──────────────────────────────────────────
    tab_edit, tab_builder = st.tabs(["📝 直接編集モード", "🧩 セクション別調整モード"])

    # ── 直接編集モード ──────────────────────────────────────────────
    with tab_edit:
        st.markdown('''<div class="hint-box" style="margin-bottom:16px;">
<div class="hint-icon">📝</div>
<div>台本を直接編集できます。文字数が目標範囲に収まるよう調整してください。</div>
</div>''', unsafe_allow_html=True)

        draft_val = st.session_state.sg_edited_draft or st.session_state.sg_draft
        edited = st.text_area(
            "台本（直接編集できます）",
            value=draft_val,
            height=520,
            key="sg_direct_edit",
        )
        char_count = len(edited)
        if char_count < target_min:
            st.warning(f"**{char_count}文字** ／ 目標 {target_min}〜{target_max}文字（あと {target_min - char_count}文字必要）")
        elif char_count > target_max:
            st.warning(f"**{char_count}文字** ／ 目標 {target_min}〜{target_max}文字（{char_count - target_max}文字オーバー）")
        else:
            st.success(f"**{char_count}文字** ／ 目標範囲内")

        col_back, col_regen, col_next = st.columns([1, 1, 2])
        with col_back:
            if st.button("← 戻る", key="tab1_back"):
                st.session_state.sg_step = 2
                st.rerun()
        with col_regen:
            if st.button("🔄 台本を再生成", key="tab1_regen"):
                try:
                    from memory_manager import get_good_elements, get_bad_patterns, get_reference_scripts
                    good_elements = get_good_elements(script_type)
                    bad_patterns = get_bad_patterns(script_type)
                    ref_scripts = get_reference_scripts(script_type)
                except Exception:
                    good_elements, bad_patterns, ref_scripts = [], [], []
                char_range = "4500〜5000文字" if script_type == "youtube" else "700〜800文字"
                with st.spinner(f"台本を再生成中... ({char_range})"):
                    try:
                        from script_crew import generate_draft
                        new_draft = generate_draft(
                            script_type=script_type,
                            selected_themes=st.session_state.sg_selected_themes,
                            selected_ideas=st.session_state.sg_selected_ideas,
                            good_elements=good_elements, bad_patterns=bad_patterns,
                            ref_scripts=ref_scripts, model=model_id,
                        )
                        st.session_state.sg_draft = new_draft
                        st.session_state.sg_edited_draft = new_draft
                        st.session_state.sg_sections = []
                        st.rerun()
                    except Exception as e:
                        st.error(f"エラー: {e}")
        with col_next:
            if st.button("ファクトチェック → 完成へ進む", type="primary", key="tab1_next",
                         use_container_width=True):
                st.session_state.sg_edited_draft = edited
                st.session_state.sg_fc_results = []
                st.session_state.sg_step = 4
                st.rerun()

    # ── セクション別調整モード ──────────────────────────────────────
    with tab_builder:
        st.markdown('''<div class="hint-box" style="margin-bottom:16px;">
<div class="hint-icon">🧩</div>
<div>台本をセクションに分割し、各セクションごとに5つの候補から最適なものを選んで組み立てます。候補はすべて全文表示されます。</div>
</div>''', unsafe_allow_html=True)

        sections = st.session_state.sg_sections

        # セクション未生成なら生成ボタン
        if not sections:
            draft_for_split = st.session_state.sg_edited_draft or st.session_state.sg_draft
            if st.button("🧩 セクション別候補を生成する（AI分割＋各5候補）", type="primary",
                         key="gen_sections", use_container_width=True):
                with st.spinner("AIが台本をセクションに分割してバリアントを生成中...（少し時間がかかります）"):
                    try:
                        import concurrent.futures
                        from script_crew import split_script_sections, generate_section_variants

                        raw_sections = split_script_sections(draft_for_split, script_type, model_id)

                        def gen(i, sec):
                            ctx = "\n\n".join(
                                raw_sections[j]["content"] for j in range(i)
                            )
                            variants = generate_section_variants(
                                sec["name"], sec["content"], ctx, script_type, model_id
                            )
                            return i, sec["name"], sec["content"], variants

                        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
                            futures = [ex.submit(gen, i, s) for i, s in enumerate(raw_sections)]
                            results = sorted(
                                [f.result() for f in concurrent.futures.as_completed(futures)],
                                key=lambda x: x[0]
                            )

                        built = []
                        for i, name, original, variants in results:
                            built.append({
                                "name": name,
                                "original": original,
                                "variants": variants,
                                "selected_idx": 0,
                            })
                            if f"sg_sec_text_{i}" not in st.session_state:
                                st.session_state[f"sg_sec_text_{i}"] = variants[0] if variants else original

                        st.session_state.sg_sections = built
                        st.rerun()
                    except Exception as e:
                        import traceback
                        st.error(f"セクション生成エラー: {e}\n{traceback.format_exc()}")
        else:
            # セクション選択UI
            for i, sec in enumerate(sections):
                st.markdown(
                    f'<div class="section-header">セクション {i+1}: {sec["name"]}</div>',
                    unsafe_allow_html=True,
                )

                prev_sel = sec.get("selected_idx", 0)
                # ラジオボタンで全5候補を一覧表示
                chosen = st.radio(
                    "候補を選択（クリックで切り替え）",
                    options=range(len(sec["variants"])),
                    format_func=lambda j, s=sec: f"候補 {j+1}　 {s['variants'][j]}",
                    index=prev_sel,
                    key=f"sg_sec_radio_{i}",
                    label_visibility="collapsed",
                )
                if chosen != prev_sel:
                    st.session_state.sg_sections[i]["selected_idx"] = chosen
                    st.session_state[f"sg_sec_text_{i}"] = sec["variants"][chosen]
                    st.rerun()

                text_key = f"sg_sec_text_{i}"
                if text_key not in st.session_state:
                    st.session_state[text_key] = (
                        sec["variants"][prev_sel] if sec["variants"] else sec["original"]
                    )
                st.text_area(
                    "微調整（直接編集可）",
                    key=text_key,
                    height=90,
                )

            # 組み上がった台本プレビュー
            assembled = "\n\n".join(
                st.session_state.get(f"sg_sec_text_{i}", s["original"])
                for i, s in enumerate(sections)
            )
            char_assembled = len(assembled)
            st.divider()
            st.markdown("#### 組み上がった台本プレビュー")
            if char_assembled < target_min:
                st.warning(f"**{char_assembled}文字** ／ 目標 {target_min}〜{target_max}文字（あと {target_min - char_assembled}文字）")
            elif char_assembled > target_max:
                st.warning(f"**{char_assembled}文字** ／ 目標 {target_min}〜{target_max}文字（{char_assembled - target_max}文字オーバー）")
            else:
                st.success(f"**{char_assembled}文字** ／ 目標範囲内")
            st.text_area("完成台本", value=assembled, height=300, disabled=True, key="sg_assembled_preview")

            col_reset, col_next = st.columns([1, 2])
            with col_reset:
                if st.button("🔄 セクションをリセット", key="reset_sections"):
                    st.session_state.sg_sections = []
                    for i in range(10):
                        st.session_state.pop(f"sg_sec_text_{i}", None)
                    st.rerun()
            with col_next:
                if st.button("この構成で確定 → ファクトチェックへ", type="primary",
                             key="confirm_sections", use_container_width=True):
                    st.session_state.sg_edited_draft = assembled
                    st.session_state.sg_fc_results = []
                    st.session_state.sg_step = 4
                    st.rerun()


# ════════════════════════════════════════════════════════════════════
# Step 4: 4モデル並列ファクトチェック + タイトル生成 + 最終調整 + 評価
# ════════════════════════════════════════════════════════════════════
elif step == 4:
    draft = st.session_state.sg_edited_draft
    script_type = st.session_state.sg_script_type
    model_id = st.session_state.sg_current_ai[0]

    st.markdown('<div class="section-header">Step 5 ／ ファクトチェック・タイトル生成・最終調整・評価</div>', unsafe_allow_html=True)

    # ────────────────────────────────────────────────────────────────
    # A) ファクトチェック未実施
    # ────────────────────────────────────────────────────────────────
    if not st.session_state.sg_fc_results:

        # 台本プレビュー
        char_preview = len(draft)
        st.markdown(
            f'''<div style="background:white;border:1px solid #E5E7EB;border-radius:12px;
padding:16px 20px;margin-bottom:18px;box-shadow:0 1px 4px rgba(0,0,0,.03);">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
<div style="background:#EEF2FF;border-radius:8px;padding:4px 10px;font-size:0.78rem;color:#4338CA;font-weight:600;">確認する台本</div>
<div style="font-size:0.78rem;color:#9CA3AF;">{char_preview}文字</div>
</div>
</div>''',
            unsafe_allow_html=True,
        )
        with st.expander("台本の全文を確認する"):
            st.text(draft)

        st.markdown("""
<div style="background:linear-gradient(135deg,#EEF2FF 0%,#F5F3FF 50%,#FDF4FF 100%);
border-radius:14px;padding:24px 28px;margin:16px 0 24px;
border:1px solid #C7D2FE;box-shadow:0 2px 12px rgba(79,70,229,.06);">
<h4 style="margin:0 0 10px;color:#1E1B4B;font-size:1.1rem;">🔬 4 AI 並列ファクトチェック</h4>
<p style="margin:0;color:#4B5563;font-size:0.88rem;line-height:1.7;">
4つのAIモデルが同時並列で台本の事実関係を独立検証します。<br>
<span style="display:inline-flex;gap:8px;margin-top:8px;flex-wrap:wrap;">
<span style="background:#F5F3FF;border-radius:6px;padding:3px 10px;font-size:0.78rem;font-weight:600;color:#7C3AED;">🟣 Claude</span>
<span style="background:#ECFDF5;border-radius:6px;padding:3px 10px;font-size:0.78rem;font-weight:600;color:#059669;">🟢 ChatGPT</span>
<span style="background:#EFF6FF;border-radius:6px;padding:3px 10px;font-size:0.78rem;font-weight:600;color:#1D4ED8;">🔵 Gemini</span>
<span style="background:#F9FAFB;border-radius:6px;padding:3px 10px;font-size:0.78rem;font-weight:600;color:#374151;">⚫ Grok</span>
</span>
</p>
</div>
""", unsafe_allow_html=True)

        col_back_fc, col_start_fc = st.columns([1, 3])
        with col_back_fc:
            if st.button("← 戻る", key="fc_back"):
                st.session_state.sg_step = 3
                st.rerun()
        with col_start_fc:
            if st.button("🚀 ファクトチェック＋タイトル生成を開始", type="primary",
                         use_container_width=True):
                result_holder = {}

                def _run_fc():
                    try:
                        from script_crew import factcheck_parallel
                        result_holder["fc"] = factcheck_parallel(draft)
                    except Exception as e:
                        result_holder["fc_error"] = str(e)

                def _run_titles():
                    try:
                        from script_crew import generate_titles
                        result_holder["titles"] = generate_titles(
                            draft=draft, script_type=script_type, model=model_id
                        )
                    except Exception as e:
                        result_holder["titles"] = f"（タイトル生成エラー: {e}）"

                t_fc = threading.Thread(target=_run_fc, daemon=True)
                t_ti = threading.Thread(target=_run_titles, daemon=True)
                t_fc.start(); t_ti.start()

                prog = st.progress(0)
                status_ph = st.empty()
                ai_status = st.empty()
                elapsed = 0
                MODEL_LABELS = ["Claude", "ChatGPT", "Gemini", "Grok"]
                while t_fc.is_alive() or t_ti.is_alive():
                    elapsed += 1
                    pct = min(90, elapsed * 2)
                    prog.progress(pct)
                    fc_s = "検証中..." if t_fc.is_alive() else "完了"
                    ti_s = "生成中..." if t_ti.is_alive() else "完了"
                    status_ph.info(f"ファクトチェック: **{fc_s}** ｜ タイトル生成: **{ti_s}**")
                    dots = "." * ((elapsed % 3) + 1)
                    ai_status.caption(f"4つのAIが並列で検証中{dots} {' / '.join(MODEL_LABELS)}")
                    time.sleep(1)
                t_fc.join(); t_ti.join()
                prog.progress(100)
                status_ph.empty(); ai_status.empty()

                if "fc_error" in result_holder:
                    st.error(f"ファクトチェックエラー: {result_holder['fc_error']}")
                else:
                    st.session_state.sg_fc_results = result_holder.get("fc", [])
                    st.session_state.sg_titles = result_holder.get("titles", "")
                    st.session_state["sg_final_sections"] = []
                    st.rerun()

    # ────────────────────────────────────────────────────────────────
    # B) ファクトチェック完了 → 結果表示 + 最終調整 + 評価
    # ────────────────────────────────────────────────────────────────
    else:
        _, ai_name = st.session_state.sg_current_ai
        titles = st.session_state.sg_titles
        fc_results = st.session_state.sg_fc_results

        # やり直しボタン
        col_redo_l, col_redo_r = st.columns([4, 1])
        with col_redo_r:
            if st.button("🔄 FCをやり直す", key="redo_fc",
                         help="ファクトチェックを最新モデルで再実行します"):
                st.session_state.sg_fc_results = []
                st.session_state.sg_titles = ""
                st.session_state["sg_final_sections"] = []
                st.rerun()

        # ─ タイトル候補カード ────────────────────────────────────────
        if titles:
            st.markdown("### 🎯 タイトル候補 ＆ サムネイルテキスト")
            import re as _re
            col_t, col_s = st.columns([3, 2])
            with col_t:
                st.markdown(
                    '<div style="background:white;border:1px solid #E5E7EB;border-radius:12px;'
                    'padding:18px 20px;box-shadow:0 1px 4px rgba(0,0,0,.03);">'
                    '<div style="font-size:0.78rem;color:#9CA3AF;margin-bottom:12px;font-weight:600;'
                    'text-transform:uppercase;letter-spacing:.06em;">'
                    'タイトル候補</div>',
                    unsafe_allow_html=True,
                )
                in_titles = False
                for line in titles.split("\n"):
                    if "タイトル" in line and line.startswith("#"):
                        in_titles = True; continue
                    if line.startswith("#"):
                        in_titles = False
                    if in_titles and line.strip():
                        st.markdown(line)
                st.markdown('</div>', unsafe_allow_html=True)
            with col_s:
                st.markdown(
                    '<div style="background:white;border:1px solid #E5E7EB;border-radius:12px;'
                    'padding:18px 20px;box-shadow:0 1px 4px rgba(0,0,0,.03);">'
                    '<div style="font-size:0.78rem;color:#9CA3AF;margin-bottom:12px;font-weight:600;'
                    'text-transform:uppercase;letter-spacing:.06em;">'
                    'サムネイル案</div>',
                    unsafe_allow_html=True,
                )
                in_thumb = False
                for line in titles.split("\n"):
                    if "サムネイル" in line and line.startswith("#"):
                        in_thumb = True; continue
                    if line.startswith("#"):
                        in_thumb = False
                    if in_thumb and line.strip():
                        st.markdown(
                            f'<div style="background:#F5F3FF;border-radius:8px;padding:10px 14px;'
                            f'margin-bottom:8px;font-size:0.88rem;border-left:3px solid #7C3AED;">{line}</div>',
                            unsafe_allow_html=True,
                        )
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")

        # ─ ファクトチェック 4カラム ───────────────────────────────────
        st.markdown("### 🔬 ファクトチェック結果（4 AI 並列）")

        MODEL_STYLES = {
            "Claude Sonnet 4.6":  {"color": "#7C3AED", "bg": "#F5F3FF", "border": "#DDD6FE", "icon": "🟣"},
            "ChatGPT (GPT-4o)":   {"color": "#059669", "bg": "#ECFDF5", "border": "#A7F3D0", "icon": "🟢"},
            "Gemini 2.5 Flash":   {"color": "#1D4ED8", "bg": "#EFF6FF", "border": "#BFDBFE", "icon": "🔵"},
            "Grok 3 Mini":        {"color": "#374151", "bg": "#F9FAFB", "border": "#D1D5DB", "icon": "⚫"},
        }
        VERDICT_MAP = {
            "✅": ("概ね正確", "#059669", "#ECFDF5"),
            "⚠️": ("一部要注意", "#D97706", "#FFFBEB"),
            "❌": ("問題あり",   "#DC2626", "#FEF2F2"),
            "❓": ("確認中",     "#6B7280", "#F9FAFB"),
        }

        # サマリーバー
        smry_cols = st.columns(4)
        for col_s2, res in zip(smry_cols, fc_results):
            if res is None:
                continue
            mname = res.get("model_name", "")
            style = MODEL_STYLES.get(mname, {"color": "#4F46E5", "bg": "#EEF2FF", "border": "#C7D2FE", "icon": "🤖"})
            verdict = res.get("verdict", "❓")
            v_label, v_color, v_bg = VERDICT_MAP.get(verdict, ("確認中", "#6B7280", "#F9FAFB"))
            with col_s2:
                st.markdown(
                    f'<div class="fc-card" style="background:{style["bg"]};'
                    f'border-color:{style["border"]};">'
                    f'<div class="model-name" style="color:{style["color"]};">{style["icon"]} {mname}</div>'
                    f'<div class="verdict">{verdict}</div>'
                    f'<div class="verdict-label" style="color:{v_color};background:{v_bg};">{v_label}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)

        # 詳細：各モデルのタブ表示
        tab_labels = [
            f'{MODEL_STYLES.get(r.get("model_name",""), {}).get("icon","🤖")} {r.get("model_name","")}'
            for r in fc_results if r
        ]
        if tab_labels:
            tabs = st.tabs(tab_labels)
            for tab, res in zip(tabs, [r for r in fc_results if r]):
                with tab:
                    if res.get("error"):
                        st.error(f"APIエラー: {res['error']}")
                    elif res.get("text"):
                        text = res["text"]
                        for line in text.split("\n"):
                            stripped = line.strip()
                            if not stripped:
                                st.markdown("")
                            elif stripped.startswith("## "):
                                st.markdown(f"**{stripped[3:]}**")
                            elif stripped.startswith("### "):
                                st.markdown(f"---\n**{stripped[4:]}**")
                            elif "✅" in stripped:
                                st.success(stripped)
                            elif "❌" in stripped:
                                st.error(stripped)
                            elif "⚠️" in stripped:
                                st.warning(stripped)
                            else:
                                st.write(stripped)

        st.markdown("---")

        # ─ 完成台本 ＋ セクション別最終調整 ─────────────────────────
        st.markdown("### 📄 完成台本 ＆ 最終調整")

        tab_view, tab_finalize = st.tabs(["👁️ 完成台本プレビュー", "🧩 セクション別最終微調整"])

        # ── プレビュータブ ──
        with tab_view:
            final_script = st.session_state.sg_edited_draft
            char_count = len(final_script)
            target_min, target_max = (4500, 5000) if script_type == "youtube" else (700, 800)
            if char_count < target_min:
                st.warning(f"**{char_count}文字** ／ 目標 {target_min}〜{target_max}文字")
            elif char_count > target_max:
                st.warning(f"**{char_count}文字** ／ 目標オーバー")
            else:
                st.success(f"**{char_count}文字** ／ 目標範囲内")

            st.text_area("完成台本", value=final_script, height=400,
                         disabled=True, key="sg_final_textarea_view")

            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button(
                    "📥 台本をダウンロード",
                    data=final_script,
                    file_name=f"script_{script_type}_{ts}.txt",
                    mime="text/plain", use_container_width=True,
                )
            with col_dl2:
                fc_text = "\n\n".join(
                    f"=== {r.get('model_name','')} ===\n{r.get('text','')}"
                    for r in fc_results if r
                )
                combined = (f"=== 完成台本 ===\n{final_script}\n\n"
                            f"=== タイトル・サムネイル案 ===\n{titles}\n\n"
                            f"=== ファクトチェック結果 ===\n{fc_text}")
                st.download_button(
                    "📥 全データをダウンロード",
                    data=combined,
                    file_name=f"script_full_{script_type}_{ts}.txt",
                    mime="text/plain", use_container_width=True,
                )

        # ── セクション別最終微調整タブ ──
        with tab_finalize:
            st.markdown('''<div class="hint-box" style="margin-bottom:16px;">
<div class="hint-icon">🧩</div>
<div>ファクトチェックの指摘を踏まえて、セクションごとに5候補から内容を選んで最終台本を組み立てます。</div>
</div>''', unsafe_allow_html=True)

            if "sg_final_sections" not in st.session_state:
                st.session_state["sg_final_sections"] = []

            final_sections = st.session_state["sg_final_sections"]
            base_script = st.session_state.sg_edited_draft

            if not final_sections:
                fc_summary = "\n".join(
                    f"[{r.get('model_name','')}の指摘] "
                    + (r.get("text","")[:400] if r.get("text") else r.get("error",""))
                    for r in fc_results if r
                )[:1200]

                if st.button("🧩 セクション別候補を生成する（ファクトチェック結果を反映）",
                             type="primary", key="gen_final_sections", use_container_width=True):
                    with st.spinner("AIがセクションを分割して各5候補を生成中..."):
                        try:
                            import concurrent.futures
                            from script_crew import split_script_sections, generate_section_variants

                            raw_secs = split_script_sections(base_script, script_type, model_id)

                            def gen_final(i, sec):
                                ctx = "\n\n".join(
                                    raw_secs[j]["content"] for j in range(i)
                                )
                                fc_ctx = f"\n\n【ファクトチェックの指摘（参考）】\n{fc_summary}"
                                variants = generate_section_variants(
                                    sec["name"], sec["content"], ctx + fc_ctx,
                                    script_type, model_id
                                )
                                return i, sec["name"], sec["content"], variants

                            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
                                futures = [ex.submit(gen_final, i, s)
                                           for i, s in enumerate(raw_secs)]
                                results = sorted(
                                    [f.result() for f in concurrent.futures.as_completed(futures)],
                                    key=lambda x: x[0]
                                )

                            built = []
                            for i, name, original, variants in results:
                                built.append({
                                    "name": name,
                                    "original": original,
                                    "variants": variants,
                                    "selected_idx": 0,
                                })
                                if f"sg_final_sec_text_{i}" not in st.session_state:
                                    st.session_state[f"sg_final_sec_text_{i}"] = (
                                        variants[0] if variants else original
                                    )
                            st.session_state["sg_final_sections"] = built
                            st.rerun()
                        except Exception as e:
                            import traceback
                            st.error(f"生成エラー: {e}\n{traceback.format_exc()}")
            else:
                target_min, target_max = (4500, 5000) if script_type == "youtube" else (700, 800)

                for i, sec in enumerate(final_sections):
                    st.markdown(
                        f'<div class="section-header">セクション {i+1}: {sec["name"]}</div>',
                        unsafe_allow_html=True,
                    )

                    prev_sel_f = sec.get("selected_idx", 0)
                    chosen_f = st.radio(
                        "候補を選択（クリックで切り替え）",
                        options=range(len(sec["variants"])),
                        format_func=lambda j, s=sec: f"候補 {j+1}　 {s['variants'][j]}",
                        index=prev_sel_f,
                        key=f"sg_fsec_radio_{i}",
                        label_visibility="collapsed",
                    )
                    if chosen_f != prev_sel_f:
                        st.session_state["sg_final_sections"][i]["selected_idx"] = chosen_f
                        st.session_state[f"sg_final_sec_text_{i}"] = sec["variants"][chosen_f]
                        st.rerun()

                    text_key_f = f"sg_final_sec_text_{i}"
                    if text_key_f not in st.session_state:
                        st.session_state[text_key_f] = (
                            sec["variants"][prev_sel_f] if sec["variants"] else sec["original"]
                        )
                    st.text_area(
                        "微調整（直接編集可）",
                        key=text_key_f,
                        height=90,
                    )

                assembled_final = "\n\n".join(
                    st.session_state.get(f"sg_final_sec_text_{i}", s["original"])
                    for i, s in enumerate(final_sections)
                )
                char_assembled = len(assembled_final)

                st.markdown("---")
                st.markdown("#### 組み上がった最終台本")
                if char_assembled < target_min:
                    st.warning(f"**{char_assembled}文字** ／ 目標 {target_min}〜{target_max}文字（あと {target_min - char_assembled}文字）")
                elif char_assembled > target_max:
                    st.warning(f"**{char_assembled}文字** ／ {char_assembled - target_max}文字オーバー")
                else:
                    st.success(f"**{char_assembled}文字** ／ 目標範囲内")
                st.text_area("最終台本", value=assembled_final, height=300,
                             disabled=True, key="sg_final_assembled")

                col_reset_f, col_fix = st.columns([1, 2])
                with col_reset_f:
                    if st.button("🔄 リセット", key="reset_final_sec"):
                        st.session_state["sg_final_sections"] = []
                        for ix in range(10):
                            st.session_state.pop(f"sg_final_sec_text_{ix}", None)
                        st.rerun()
                with col_fix:
                    if st.button("この台本で確定する", type="primary", key="fix_final_script",
                                 use_container_width=True):
                        st.session_state.sg_edited_draft = assembled_final
                        st.session_state["sg_final_sections"] = []
                        for ix in range(10):
                            st.session_state.pop(f"sg_final_sec_text_{ix}", None)
                        st.success("最終台本を確定しました！「完成台本プレビュー」タブで確認・ダウンロードできます")
                        st.rerun()

        st.markdown("---")

        # ─ 評価フロー ────────────────────────────────────────────────
        final_script_for_rating = st.session_state.sg_edited_draft
        theme = (st.session_state.sg_selected_themes[0]
                 if st.session_state.sg_selected_themes else "不明")
        angle_key = st.session_state.sg_current_angle[0]
        rating_mode = st.session_state.sg_rating_mode

        if rating_mode is None:
            st.markdown("""
<div class="rating-card" style="background:linear-gradient(135deg,#F0FDF4,#ECFDF5);border-color:#A7F3D0;">
<h4 style="margin:0 0 8px;color:#065F46;font-size:1.05rem;">この台本を評価してください</h4>
<p style="margin:0;color:#047857;font-size:0.86rem;line-height:1.6;">
評価結果をAIが分析し、次回の台本生成に自動で反映されます。<br>
好評ポイント・改善パターンを学習して、あなた好みの台本精度が向上します。
</p>
</div>
""", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            col_good, col_bad = st.columns(2)
            with col_good:
                if st.button("👍 良い台本だった", type="primary", use_container_width=True):
                    st.session_state.sg_rating_mode = "good"
                    st.rerun()
            with col_bad:
                if st.button("👎 改善が必要", use_container_width=True):
                    st.session_state.sg_rating_mode = "bad"
                    st.rerun()

        elif rating_mode == "good":
            if not st.session_state.sg_learned_elements:
                with st.spinner("台本の好評ポイントをAIが分析中..."):
                    try:
                        from script_crew import analyze_good_elements
                        elements = analyze_good_elements(final_script_for_rating, script_type, model_id)
                    except Exception:
                        elements = []
                    try:
                        from memory_manager import save_script, record_theme_used
                        from memory_manager import _load_history, _save_history, _type_data
                        save_script(script=final_script_for_rating, rating="good", theme=theme,
                                    script_type=script_type, angle=angle_key)
                        record_theme_used(theme=theme, script_type=script_type, angle=angle_key)
                        if elements:
                            history = _load_history()
                            td = _type_data(history, script_type)
                            for el in elements:
                                if el not in td["good_elements"]:
                                    td["good_elements"].append(el)
                            td["good_elements"] = td["good_elements"][-30:]
                            _save_history(history)
                    except Exception as e:
                        st.error(f"保存エラー: {e}")
                    st.session_state.sg_learned_elements = elements if elements else ["（分析データなし）"]
                    st.session_state.sg_saved = True
                    st.rerun()
            else:
                st.markdown("""
<div class="rating-card" style="background:#ECFDF5;border-color:#6EE7B7;">
<h4 style="color:#065F46;margin:0 0 8px;">好評として保存しました</h4>
<p style="color:#047857;margin:0;font-size:0.86rem;">次回の台本生成に自動反映されます</p>
</div>
""", unsafe_allow_html=True)
                elements = st.session_state.sg_learned_elements
                if elements and elements != ["（分析データなし）"]:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("**今回学習した好評ポイント**")
                    for el in elements:
                        st.markdown(
                            f'<div style="background:#F0FDF4;border-left:3px solid #059669;'
                            f'padding:10px 14px;border-radius:0 8px 8px 0;margin:6px 0;font-size:0.88rem;'
                            f'line-height:1.6;">'
                            f'{el}</div>',
                            unsafe_allow_html=True,
                        )

        elif rating_mode == "bad":
            if not st.session_state.sg_saved:
                st.markdown("""
<div class="rating-card" style="background:#FEF2F2;border-color:#FECACA;">
<h4 style="color:#991B1B;margin:0 0 6px;">改善フィードバック</h4>
<p style="color:#B91C1C;margin:0;font-size:0.86rem;">何が問題だったか教えてください。次回の生成に反映されます。</p>
</div>
""", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                ng_themes = st.multiselect(
                    "NGにするテーマ", options=st.session_state.sg_selected_themes,
                    default=[], key="sg_bad_ng_themes",
                )
                ng_ideas = st.multiselect(
                    "NGにするアイデア", options=st.session_state.sg_selected_ideas or [],
                    default=[], key="sg_bad_ng_ideas",
                )
                bad_note = st.text_input(
                    "悪かった点を一言で（任意）",
                    placeholder="例：感情訴求が弱かった、情報が古かった など",
                    key="sg_bad_note",
                )
                if st.button("フィードバックを保存して学習させる", type="primary",
                             use_container_width=True):
                    with st.spinner("AIが改善パターンを分析中..."):
                        try:
                            from script_crew import analyze_bad_pattern
                            pattern = analyze_bad_pattern(
                                final_script_for_rating, script_type, bad_note, model_id)
                        except Exception:
                            pattern = bad_note if bad_note else ""
                        try:
                            from memory_manager import (save_script, record_theme_used,
                                add_rejected_themes, add_rejected_ideas,
                                _load_history, _save_history, _type_data)
                            save_script(script=final_script_for_rating, rating="bad",
                                        theme=theme, script_type=script_type, angle=angle_key)
                            record_theme_used(theme=theme, script_type=script_type, angle=angle_key)
                            if ng_themes:
                                add_rejected_themes(ng_themes, script_type)
                            if ng_ideas:
                                add_rejected_ideas(ng_ideas, script_type)
                            if pattern:
                                history = _load_history()
                                td = _type_data(history, script_type)
                                if pattern not in td["bad_patterns"]:
                                    td["bad_patterns"].append(pattern)
                                td["bad_patterns"] = td["bad_patterns"][-30:]
                                _save_history(history)
                        except Exception as e:
                            st.error(f"保存エラー: {e}")
                    st.session_state.sg_learned_pattern = pattern
                    st.session_state.sg_saved = True
                    st.rerun()
            else:
                st.markdown("""
<div class="rating-card" style="background:#FFFBEB;border-color:#FDE68A;">
<h4 style="color:#92400E;margin:0 0 6px;">改善フィードバックを保存しました</h4>
<p style="color:#B45309;margin:0;font-size:0.86rem;">次回の生成に反映されます</p>
</div>
""", unsafe_allow_html=True)
                if st.session_state.sg_learned_pattern:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown(
                        f'<div style="background:#FFFBEB;border-left:3px solid #D97706;'
                        f'padding:10px 14px;border-radius:0 8px 8px 0;font-size:0.88rem;line-height:1.6;">'
                        f'<b>学習した改善パターン:</b> {st.session_state.sg_learned_pattern}</div>',
                        unsafe_allow_html=True,
                    )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 新しい台本を生成する", use_container_width=True):
            reset_all()
            st.rerun()


# ─── フッター ─────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
if step > 0:
    if st.button("↩️ 最初からやり直す", type="secondary"):
        reset_all()
        st.rerun()

st.markdown('''
<div class="app-footer">
台本生成システム v2.0 — AI マルチエージェント × 4モデル並列ファクトチェック
</div>
''', unsafe_allow_html=True)
