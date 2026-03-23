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
        # セクションビルダー（廃止済み・互換性のため残す）
        "sg_section_mode": False,
        "sg_sections": [],
        # 台本バリアント（10パターン）
        "sg_draft_variants": [],
        "sg_selected_variant_idx": 0,
        "sg_variant_error": "",
        # ファクトチェック
        "sg_fc_results": [],
        # 部分ブラッシュアップ
        "sg_brushup_candidates": [],
        "sg_brushup_original": "",
        "sg_brushup_generating": False,
        # テーマピッカー開閉フラグ
        "sg_theme_picker_open": False,
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
        # ── テーマカードグリッドピッカー ──────────────────────────────
        selected_plain = st.session_state.sg_selected_themes or []
        picker_open = st.session_state.get("sg_theme_picker_open", False)

        if not picker_open:
            # ── 閉じた状態：選択済みチップ＋「選ぶ」ボタン ──
            if selected_plain:
                chips_html = " ".join([
                    f'<span style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:20px;'
                    f'padding:5px 14px;font-size:0.83rem;color:#1D4ED8;font-weight:600;">{t[:30]}</span>'
                    for t in selected_plain
                ])
                st.markdown(f'<div style="margin-bottom:10px;line-height:2.2;">{chips_html}</div>',
                            unsafe_allow_html=True)
            col_open_btn, col_cnt = st.columns([4, 1])
            with col_open_btn:
                if st.button("📋 テーマを選ぶ / 変更する", use_container_width=True, key="sg_open_picker"):
                    st.session_state["sg_theme_picker_open"] = True
                    st.rerun()
            with col_cnt:
                if selected_plain:
                    st.markdown(
                        f'<div style="text-align:center;padding:8px;font-size:0.9rem;'
                        f'color:#4338CA;font-weight:700;">{len(selected_plain)}/3</div>',
                        unsafe_allow_html=True)
        else:
            # ── 開いた状態：全幅カードグリッド ──
            n_sel = len(selected_plain)
            st.markdown(
                '<div style="background:linear-gradient(135deg,#EEF2FF,#F5F3FF);border-radius:14px;'
                'padding:14px 20px;margin-bottom:18px;border:1px solid #C7D2FE;">'
                '<div style="font-weight:700;color:#1E1B4B;font-size:0.97rem;">テーマを選んでください（最大3個）</div>'
                '<div style="font-size:0.8rem;color:#6B7280;margin-top:4px;">'
                '「選択する」をクリック → 「決定」で確定</div></div>',
                unsafe_allow_html=True,
            )
            COLS = 3
            for row_start in range(0, len(themes), COLS):
                row_themes = themes[row_start:row_start + COLS]
                cols_g = st.columns(COLS)
                for ci, (col_g, theme_raw) in enumerate(zip(cols_g, row_themes)):
                    plain = _strip_num_t(theme_raw)
                    is_sel = plain in selected_plain
                    # タイトルと補足に分割（｜区切り）
                    if '｜' in plain:
                        title_p, sub_p = plain.split('｜', 1)
                        title_p = title_p.strip(); sub_p = sub_p.strip()
                    else:
                        title_p = plain; sub_p = ""
                    with col_g:
                        bg = "#EFF6FF" if is_sel else "white"
                        bdr = "2px solid #3B82F6" if is_sel else "1px solid #E5E7EB"
                        tc = "#1D4ED8" if is_sel else "#1F2937"
                        chk = "✓ " if is_sel else ""
                        sub_html = (f'<ul style="margin:6px 0 0 0;padding-left:16px;'
                                    f'font-size:0.75rem;color:#6B7280;line-height:1.55;">'
                                    f'<li>{sub_p}</li></ul>') if sub_p else ""
                        st.markdown(
                            f'<div style="background:{bg};border:{bdr};border-radius:12px;'
                            f'padding:14px 16px;min-height:90px;margin-bottom:4px;">'
                            f'<div style="font-weight:700;font-size:0.85rem;color:{tc};line-height:1.4;">'
                            f'{chk}{title_p}</div>{sub_html}</div>',
                            unsafe_allow_html=True,
                        )
                        is_disabled = (not is_sel and n_sel >= 3)
                        btn_lbl = "✓ 選択中" if is_sel else "選択する"
                        btn_type = "primary" if is_sel else "secondary"
                        if st.button(btn_lbl, key=f"sg_tc_{row_start + ci}",
                                     disabled=is_disabled, use_container_width=True,
                                     type=btn_type):
                            if is_sel:
                                st.session_state.sg_selected_themes = [t for t in selected_plain if t != plain]
                            else:
                                st.session_state.sg_selected_themes = selected_plain + [plain]
                            st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            c_close, c_confirm = st.columns([1, 2])
            with c_close:
                if st.button("✕ 閉じる", use_container_width=True, key="sg_close_picker"):
                    st.session_state["sg_theme_picker_open"] = False
                    st.rerun()
            with c_confirm:
                n_sel2 = len(st.session_state.sg_selected_themes or [])
                if st.button(f"✅ 決定（{n_sel2}個選択中）", type="primary",
                             disabled=n_sel2 == 0, use_container_width=True, key="sg_confirm_picker"):
                    st.session_state["sg_theme_picker_open"] = False
                    st.rerun()

        # ── 後続ロジック用に selected を定義 ──────────────────────────
        selected = st.session_state.sg_selected_themes or []

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
            bg = "#F5F3FF"  # 全て薄い紫で統一
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
                        st.session_state["sg_draft_variants"] = []
                        st.session_state["sg_selected_variant_idx"] = 0
                        st.session_state.sg_step = 3
                        st.rerun()
                    except Exception as e:
                        import traceback
                        st.error(f"エラー:\n{e}\n\n{traceback.format_exc()}")


# ════════════════════════════════════════════════════════════════════
# Step 3: 5種類の切り口で台本を選択・編集
# ════════════════════════════════════════════════════════════════════
elif step == 3:
    _, ai_name = st.session_state.sg_current_ai
    script_type = st.session_state.sg_script_type
    model_id = st.session_state.sg_current_ai[0]
    target_min, target_max = (4500, 5000) if script_type == "youtube" else (700, 800)

    st.markdown('<div class="section-header">Step 4 ／ 台本を選んで編集</div>', unsafe_allow_html=True)
    st.markdown(f'''<div style="display:flex;gap:10px;margin-bottom:18px;flex-wrap:wrap;">
<div style="background:#F0FDF4;border-radius:8px;padding:5px 12px;font-size:0.81rem;color:#059669;font-weight:600;">🤖 {ai_name}</div>
<div style="background:#EEF2FF;border-radius:8px;padding:5px 12px;font-size:0.81rem;color:#4338CA;font-weight:600;">📏 目標 {target_min}〜{target_max}文字</div>
</div>''', unsafe_allow_html=True)

    variants = st.session_state.get("sg_draft_variants", [])

    # ── アングル定義（UIとscript_crewで共通） ───────────────────────
    ANGLE_ICONS = {
        "science":    "🔬", "emotion":  "💗", "story":   "📖",
        "debate":     "⚡", "action":   "🚀", "ranking": "🏆",
        "howto":      "🛠️", "psychology":"🧠", "trend":  "📈",
        "expert":     "👑",
    }
    ANGLE_COLORS = {
        "science":    ("#1D4ED8", "#EFF6FF", "#BFDBFE"),
        "emotion":    ("#BE185D", "#FDF2F8", "#FBCFE8"),
        "story":      ("#065F46", "#F0FDF4", "#A7F3D0"),
        "debate":     ("#92400E", "#FFFBEB", "#FDE68A"),
        "action":     ("#7C3AED", "#F5F3FF", "#DDD6FE"),
        "ranking":    ("#B45309", "#FFF7ED", "#FED7AA"),
        "howto":      ("#0F766E", "#F0FDFA", "#99F6E4"),
        "psychology": ("#6D28D9", "#F5F3FF", "#EDE9FE"),
        "trend":      ("#0369A1", "#F0F9FF", "#BAE6FD"),
        "expert":     ("#9D174D", "#FFF1F2", "#FFE4E6"),
    }

    # ── A) 自動生成（未生成の場合はボタンなしで自動スタート） ───────
    if not variants:
        gen_error = st.session_state.get("sg_variant_error", "")
        if gen_error:
            st.error(f"生成エラーが発生しました：{gen_error}")
            col_bk_e, col_retry = st.columns([1, 2])
            with col_bk_e:
                if st.button("← アイデア選択に戻る", key="s3_back_err"):
                    st.session_state["sg_variant_error"] = ""
                    st.session_state.sg_step = 2
                    st.rerun()
            with col_retry:
                if st.button("🔄 再試行", type="primary", key="s3_retry", use_container_width=True):
                    st.session_state["sg_variant_error"] = ""
                    st.rerun()
        else:
            # 自動生成を実行
            with st.spinner("10種の切り口で台本を並列生成中... しばらくお待ちください（1〜2分）"):
                try:
                    from memory_manager import (get_good_elements, get_bad_patterns,
                                                get_reference_scripts, get_edit_improvements)
                    good_elements = get_good_elements(script_type)
                    bad_patterns = get_bad_patterns(script_type)
                    ref_scripts = get_reference_scripts(script_type)
                    edit_improvements = get_edit_improvements(script_type)
                except Exception:
                    good_elements, bad_patterns, ref_scripts, edit_improvements = [], [], [], []
                try:
                    from script_crew import generate_draft_variants
                    result = generate_draft_variants(
                        script_type=script_type,
                        selected_themes=st.session_state.sg_selected_themes,
                        selected_ideas=st.session_state.sg_selected_ideas,
                        good_elements=good_elements,
                        bad_patterns=bad_patterns,
                        ref_scripts=ref_scripts,
                        model=model_id,
                        edit_improvements=edit_improvements,
                    )
                    st.session_state["sg_draft_variants"] = result
                    st.session_state["sg_selected_variant_idx"] = 0
                    st.session_state["sg_variant_error"] = ""
                    st.session_state.sg_draft = result[0]["draft"]
                    st.session_state.sg_edited_draft = result[0]["draft"]
                    # テキストエリアのキャッシュをクリア
                    st.session_state.pop("sg_direct_edit_v2", None)
                    st.rerun()
                except Exception as e:
                    import traceback
                    st.session_state["sg_variant_error"] = f"{e}\n{traceback.format_exc()}"
                    st.rerun()

    # ── B) バリアント生成済み → 選択＋編集 ────────────────────────
    else:
        sel_idx = st.session_state.get("sg_selected_variant_idx", 0)
        # 範囲外チェック
        if sel_idx >= len(variants):
            sel_idx = 0
            st.session_state["sg_selected_variant_idx"] = 0

        # ── 選択カード（5枚 × 2行） ──────────────────────────────
        st.markdown("**① 切り口を選んでください**")
        row1_variants = variants[:5]
        row2_variants = variants[5:] if len(variants) > 5 else []

        def _render_angle_row(row_variants, offset):
            cols = st.columns(len(row_variants))
            for ci_local, v in enumerate(row_variants):
                ci = ci_local + offset
                ak = v["angle_key"]
                icon = ANGLE_ICONS.get(ak, "✍️")
                txt_color, bg, border = ANGLE_COLORS.get(ak, ("#4F46E5", "#EEF2FF", "#C7D2FE"))
                is_sel = (ci == sel_idx)
                card_bg = bg if is_sel else "white"
                card_border = border if is_sel else "#E5E7EB"
                shadow = f"0 0 0 3px {border}" if is_sel else "none"
                with cols[ci_local]:
                    st.markdown(
                        f'<div style="background:{card_bg};border:2px solid {card_border};'
                        f'border-radius:12px;padding:10px 6px;text-align:center;'
                        f'box-shadow:{shadow};min-height:68px;display:flex;flex-direction:column;'
                        f'align-items:center;justify-content:center;">'
                        f'<div style="font-size:1.3rem;">{icon}</div>'
                        f'<div style="font-size:0.68rem;font-weight:700;color:{txt_color};'
                        f'margin-top:3px;line-height:1.3;">{v["angle_name"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button("選択" if not is_sel else "✓ 選択中",
                                 key=f"sel_variant_{ci}",
                                 type="primary" if is_sel else "secondary",
                                 use_container_width=True):
                        # テキストエリアのキャッシュを必ずクリアしてから切り替え
                        st.session_state.pop("sg_direct_edit_v2", None)
                        st.session_state["sg_selected_variant_idx"] = ci
                        st.session_state.sg_draft = variants[ci]["draft"]
                        st.session_state.sg_edited_draft = variants[ci]["draft"]
                        st.rerun()

        _render_angle_row(row1_variants, 0)
        if row2_variants:
            st.markdown('<div style="margin-top:8px;"></div>', unsafe_allow_html=True)
            _render_angle_row(row2_variants, 5)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**② 台本を確認・編集してください**")

        ak_sel = variants[sel_idx]["angle_key"]
        txt_c, bg_c, border_c = ANGLE_COLORS.get(ak_sel, ("#4F46E5", "#EEF2FF", "#C7D2FE"))
        icon_sel = ANGLE_ICONS.get(ak_sel, "✍️")
        st.markdown(
            f'<div style="background:{bg_c};border-left:4px solid {txt_c};border-radius:0 10px 10px 0;'
            f'padding:10px 16px;margin-bottom:12px;font-size:0.88rem;color:{txt_c};font-weight:600;">'
            f'{icon_sel} 現在選択中：{variants[sel_idx]["angle_name"]}</div>',
            unsafe_allow_html=True,
        )

        # テキストエリア：session_state に値がある場合はそれを、なければ sg_edited_draft を使う
        _ta_key = "sg_direct_edit_v2"
        if _ta_key not in st.session_state:
            st.session_state[_ta_key] = st.session_state.sg_edited_draft
        edited = st.text_area(
            "台本（直接編集できます）",
            height=500,
            key=_ta_key,
        )
        char_count = len(edited)
        if char_count < target_min:
            st.warning(f"**{char_count}文字** ／ 目標 {target_min}〜{target_max}文字（あと {target_min - char_count}文字）")
        elif char_count > target_max:
            st.warning(f"**{char_count}文字** ／ {char_count - target_max}文字オーバー")
        else:
            st.success(f"**{char_count}文字** ／ 目標範囲内 ✓")

        col_bk2, col_regen2, col_next2 = st.columns([1, 1, 2])
        with col_bk2:
            if st.button("← 戻る", key="s3_back_edit"):
                st.session_state.sg_step = 2
                st.rerun()
        with col_regen2:
            if st.button("🔄 再生成", key="s3_regen"):
                st.session_state["sg_draft_variants"] = []
                st.session_state["sg_selected_variant_idx"] = 0
                st.session_state["sg_variant_error"] = ""
                st.session_state.sg_draft = ""
                st.session_state.sg_edited_draft = ""
                st.session_state.pop("sg_direct_edit_v2", None)
                st.rerun()
        with col_next2:
            if st.button("ファクトチェック → 完成へ進む", type="primary",
                         key="s3_next", use_container_width=True):
                st.session_state.sg_edited_draft = edited
                # ── 編集差分が大きい場合は改善ルールを自動学習 ──
                original_draft = variants[sel_idx]["draft"]
                edit_diff = abs(len(edited) - len(original_draft))
                content_changed = edited.strip() != original_draft.strip()
                if content_changed and edit_diff > 50:
                    try:
                        from script_crew import analyze_edit_improvements, consolidate_improvement_rules
                        from memory_manager import get_edit_improvements, save_edit_improvements
                        new_rules = analyze_edit_improvements(
                            original_draft, edited, script_type, model_id
                        )
                        if new_rules:
                            current_rules = get_edit_improvements(script_type)
                            consolidated = consolidate_improvement_rules(
                                current_rules, new_rules, script_type, model_id
                            )
                            save_edit_improvements(consolidated, script_type)
                            st.session_state["sg_last_learned_rules"] = consolidated
                    except Exception:
                        pass
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
    # 直前に学習したルールがあれば表示
    last_rules = st.session_state.get("sg_last_learned_rules", [])
    if last_rules:
        rules_html = "".join(
            f'<div style="display:flex;gap:8px;margin-bottom:6px;">'
            f'<span style="color:#059669;font-weight:700;flex-shrink:0;">✓</span>'
            f'<span style="font-size:0.85rem;color:#065F46;">{r}</span></div>'
            for r in last_rules
        )
        st.markdown(
            f'<div style="background:#ECFDF5;border:1px solid #A7F3D0;border-radius:12px;'
            f'padding:14px 18px;margin-bottom:16px;">'
            f'<div style="font-weight:700;color:#065F46;margin-bottom:8px;">✨ 編集内容を学習しました — 次回の生成から自動反映されます</div>'
            f'{rules_html}</div>',
            unsafe_allow_html=True,
        )
        st.session_state["sg_last_learned_rules"] = []  # 一度だけ表示

    # ────────────────────────────────────────────────────────────────
    # A) ファクトチェック未実施 → 自動で開始
    if not st.session_state.sg_fc_results:

        st.markdown("""
<div style="background:linear-gradient(135deg,#EEF2FF 0%,#F5F3FF 50%,#FDF4FF 100%);
border-radius:14px;padding:24px 28px;margin:0 0 24px;
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
            if st.button("🔄 やり直す", key="fc_retry"):
                st.rerun()
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

        # ─ 完成台本 ＆ 最終調整 ──────────────────────────────────
        st.markdown("### 📄 完成台本 ＆ 最終調整")

        target_min, target_max = (4500, 5000) if script_type == "youtube" else (700, 800)
        final_script = st.session_state.sg_edited_draft
        char_count = len(final_script)

        # 文字数バッジ
        if char_count < target_min:
            st.warning(f"**{char_count}文字** ／ 目標 {target_min}〜{target_max}文字（あと {target_min - char_count}文字）")
        elif char_count > target_max:
            st.warning(f"**{char_count}文字** ／ {char_count - target_max}文字オーバー")
        else:
            st.success(f"**{char_count}文字** ／ 目標範囲内 ✓")

        # 直接編集テキストエリア
        edited_final = st.text_area(
            "台本（ここで最終編集できます）",
            value=final_script,
            height=420,
            key="sg_final_edit_area",
        )
        char_after = len(edited_final)
        if char_after != char_count:
            if char_after < target_min:
                st.caption(f"📝 編集後: {char_after}文字（あと {target_min - char_after}文字）")
            elif char_after > target_max:
                st.caption(f"📝 編集後: {char_after}文字（{char_after - target_max}文字オーバー）")
            else:
                st.caption(f"📝 編集後: {char_after}文字 ✓")

        # テキストエリアの変更を即時反映
        if edited_final != final_script:
            st.session_state.sg_edited_draft = edited_final

        st.markdown("---")

        # ── 部分ブラッシュアップ ────────────────────────────────────────
        st.markdown("""
<div style="background:linear-gradient(135deg,#F0F9FF 0%,#EFF6FF 100%);
border-radius:14px;padding:16px 22px;margin-bottom:16px;border:1px solid #BAE6FD;">
<h4 style="margin:0 0 4px;color:#0C4A6E;font-size:1.05rem;">✏️ 部分ブラッシュアップ</h4>
<p style="margin:0;color:#0369A1;font-size:0.84rem;line-height:1.6;">
改善したいブロックにチェックを入れてください（複数選択可）。方向性を選んで候補を生成し、気に入った候補で差し替えられます。
</p>
</div>
""", unsafe_allow_html=True)

        # ── ブロック一覧（チェックボックスで複数選択）──
        current_script_for_bu = st.session_state.sg_edited_draft
        blocks = [b.strip() for b in current_script_for_bu.split("\n\n") if b.strip()]
        if len(blocks) <= 2:
            blocks = [b.strip() for b in current_script_for_bu.split("\n") if b.strip()]

        # セッション: 選択済みブロックindexリスト
        if "sg_brushup_checked" not in st.session_state:
            st.session_state["sg_brushup_checked"] = []

        st.markdown("**① 改善したいブロックを選択（複数可）**")
        new_checked = []
        for bi, block in enumerate(blocks):
            is_checked = bi in st.session_state["sg_brushup_checked"]
            col_chk, col_blk = st.columns([1, 15])
            with col_chk:
                checked = st.checkbox("", value=is_checked, key=f"sg_blk_chk_{bi}", label_visibility="collapsed")
            with col_blk:
                bg = "#EFF6FF" if checked else "#FAFAFA"
                border = "2px solid #3B82F6" if checked else "1px solid #E5E7EB"
                # テキスト省略なし・全文表示
                st.markdown(
                    f'<div style="background:{bg};border:{border};border-radius:8px;'
                    f'padding:10px 14px;font-size:0.85rem;line-height:1.6;color:#374151;'
                    f'white-space:pre-wrap;word-break:break-word;">'
                    f'{block}</div>',
                    unsafe_allow_html=True,
                )
            if checked:
                new_checked.append(bi)

        st.session_state["sg_brushup_checked"] = new_checked

        # 選択中ブロックを取得（インデックスも保持して前後コンテキスト用に使う）
        selected_indices = [i for i in new_checked if i < len(blocks)]
        selected_blocks = [blocks[i] for i in selected_indices]

        st.markdown("<br>", unsafe_allow_html=True)

        # ── 選択中ブロック表示 + 方向性 ──
        if selected_blocks:
            combined_preview = "\n\n".join(selected_blocks)
            st.markdown(
                f'<div style="background:#EFF6FF;border:2px solid #3B82F6;border-radius:10px;'
                f'padding:12px 16px;margin-bottom:12px;">'
                f'<div style="font-size:0.75rem;color:#1D4ED8;font-weight:600;margin-bottom:6px;">'
                f'選択中のブロック（{len(selected_blocks)}件）</div>'
                f'<div style="font-size:0.88rem;color:#1E3A5F;line-height:1.7;white-space:pre-wrap;">'
                f'{combined_preview}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            col_preset, col_n = st.columns([3, 1])
            with col_preset:
                # ── プリセット読み込み（Supabase永続化） ──
                try:
                    from memory_manager import get_brushup_presets
                    _loaded_presets = get_brushup_presets(script_type)
                except Exception:
                    _loaded_presets = [
                        "別のニュアンスで書き直す", "もっと感情的・共感的に",
                        "より簡潔にまとめる", "インパクトを強くする",
                    ]
                BRUSHUP_PRESETS = _loaded_presets + ["カスタム指示を入力..."]

                preset = st.selectbox("② 改善の方向性", BRUSHUP_PRESETS, key="sg_brushup_preset")
                if preset == "カスタム指示を入力...":
                    custom_inst = st.text_input(
                        "具体的な指示",
                        placeholder="例：もっと驚きのある書き出しにして",
                        key="sg_brushup_custom",
                    )
                    brushup_instruction = custom_inst if custom_inst else "より良い表現に書き直す"
                else:
                    brushup_instruction = preset

                # ── 方向性を管理するエクスパンダー ──
                with st.expander("⚙️ 方向性の選択肢を管理する"):
                    st.caption("選択肢の追加・削除ができます。変更はSupabaseに保存されます。")
                    # 追加
                    col_new, col_add = st.columns([4, 1])
                    with col_new:
                        new_preset_text = st.text_input(
                            "新しい方向性を追加",
                            placeholder="例：関西弁に変換する",
                            key="sg_brushup_new_preset",
                            label_visibility="collapsed",
                        )
                    with col_add:
                        if st.button("追加", key="sg_brushup_add_preset", use_container_width=True):
                            if new_preset_text.strip():
                                try:
                                    from memory_manager import get_brushup_presets, save_brushup_presets
                                    current_presets = get_brushup_presets(script_type)
                                    if new_preset_text.strip() not in current_presets:
                                        current_presets.append(new_preset_text.strip())
                                        save_brushup_presets(current_presets, script_type)
                                        st.success("追加しました")
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"保存エラー: {e}")
                    # 現在の一覧と削除ボタン
                    st.markdown("**現在の選択肢：**")
                    for pi, p in enumerate(_loaded_presets):
                        col_pl, col_pd = st.columns([5, 1])
                        with col_pl:
                            st.markdown(
                                f'<div style="font-size:0.85rem;padding:4px 8px;'
                                f'background:#F8FAFC;border-radius:6px;margin:2px 0;">{p}</div>',
                                unsafe_allow_html=True,
                            )
                        with col_pd:
                            if st.button("削除", key=f"sg_del_preset_{pi}", use_container_width=True):
                                try:
                                    from memory_manager import get_brushup_presets, save_brushup_presets
                                    updated = [x for x in get_brushup_presets(script_type) if x != p]
                                    save_brushup_presets(updated, script_type)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"削除エラー: {e}")

            with col_n:
                n_cands = st.radio("③ 候補数", [2, 3, 4], index=1, horizontal=False, key="sg_brushup_n")

            if st.button("🪄 候補を生成する", type="primary", use_container_width=True, key="sg_brushup_btn"):
                with st.spinner(f"AIが{len(selected_blocks)}ブロック分の候補を並列生成中..."):
                    try:
                        from script_crew import generate_brushup_candidates
                        import concurrent.futures as _cf

                        def _gen(block_text):
                            cands = generate_brushup_candidates(
                                target_text=block_text,
                                instruction=brushup_instruction,
                                n_candidates=n_cands,
                                script_type=script_type,
                                model=model_id,
                            )
                            return {"original": block_text, "original_before": block_text, "candidates": cands, "applied": False}

                        with _cf.ThreadPoolExecutor(max_workers=len(selected_blocks)) as _ex:
                            per_block = list(_ex.map(_gen, selected_blocks))

                        st.session_state["sg_brushup_per_block"] = per_block
                        st.session_state["sg_brushup_candidates"] = []   # 旧キーをクリア
                    except Exception as e:
                        st.error(f"生成エラー: {e}")

        # ── 候補表示（ブロックごとに独立表示・個別差し替え）──
        per_block = st.session_state.get("sg_brushup_per_block", [])

        if per_block:
            st.markdown("---")
            st.markdown(
                '<div style="background:linear-gradient(135deg,#EEF2FF,#F5F3FF);'
                'border-radius:12px;padding:10px 18px;margin-bottom:18px;border:1px solid #C7D2FE;">'
                '<div style="font-weight:700;color:#3730A3;font-size:0.92rem;">🪄 全体の流れを確認しながら候補を選んでください</div>'
                '<div style="color:#4338CA;font-size:0.8rem;margin-top:3px;">'
                '変更対象のブロックごとに候補が表示されます。ラジオで選択 → 最後に「差し替える」で確定。</div></div>',
                unsafe_allow_html=True,
            )

            import re as _re2

            # 全文をブロック分割してインライン表示
            full_script = st.session_state.sg_edited_draft
            all_paragraphs = [p.strip() for p in full_script.split("\n\n") if p.strip()]

            # per_block の original をキーにしたルックアップ（テキスト → (index, info)）
            orig_lookup = {b["original"].strip(): (bi, b) for bi, b in enumerate(per_block)}

            for para_i, para_text in enumerate(all_paragraphs):
                if para_text in orig_lookup:
                    bi, block_info = orig_lookup[para_text]
                    block_cands = block_info["candidates"]
                    applied     = block_info["applied"]

                    if applied:
                        # 差し替え済みは通常テキストとして表示
                        st.markdown(
                            f'<div style="padding:8px 14px;margin:2px 0;font-size:0.86rem;'
                            f'color:#374151;line-height:1.7;white-space:pre-wrap;">{para_text}</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        # 変更前ブロック → オレンジ背景で表示
                        st.markdown(
                            f'<div style="background:#FFF7ED;border-left:3px solid #FB923C;'
                            f'border-radius:0 8px 8px 0;padding:10px 14px;margin:4px 0 2px;'
                            f'font-size:0.86rem;color:#374151;line-height:1.7;white-space:pre-wrap;">{para_text}</div>',
                            unsafe_allow_html=True,
                        )

                        # 候補：小さいチェックボックスを左前に配置
                        active_key = f"sg_active_cand_{bi}"
                        active_i = st.session_state.get(active_key, 0)
                        if active_i >= len(block_cands):
                            active_i = 0

                        for ci, cand in enumerate(block_cands):
                            is_active = (ci == active_i)
                            bg     = "#EFF6FF" if is_active else "#F9FAFB"
                            border = "2px solid #3B82F6" if is_active else "1px solid #E5E7EB"
                            col_chk, col_txt = st.columns([0.3, 9])
                            with col_chk:
                                checked = st.checkbox(
                                    "", value=is_active,
                                    key=f"sg_chk_{bi}_{ci}",
                                )
                                if checked and not is_active:
                                    st.session_state[active_key] = ci
                                    st.rerun()
                            with col_txt:
                                st.markdown(
                                    f'<div style="background:{bg};border:{border};border-radius:8px;'
                                    f'padding:10px 14px;margin:2px 0;">'
                                    f'<div style="font-size:0.86rem;color:#1F2937;line-height:1.7;white-space:pre-wrap;">{cand}</div></div>',
                                    unsafe_allow_html=True,
                                )

                        # 差し替えボタン
                        _, col_b = st.columns([18, 2])
                        with col_b:
                            if st.button("✅ 差し替える", type="primary",
                                         key=f"sg_apply_b{bi}", use_container_width=True):
                                chosen = st.session_state.get(active_key, 0)
                                chosen_text = block_cands[chosen]
                                current = st.session_state.sg_edited_draft
                                if para_text in current:
                                    new_script = current.replace(para_text, chosen_text, 1)
                                    new_script = _re2.sub(r'\n{3,}', '\n\n', new_script).strip()
                                    st.session_state.sg_edited_draft = new_script
                                    st.session_state["sg_brushup_per_block"][bi]["applied"] = True
                                    st.session_state["sg_brushup_per_block"][bi]["chosen"] = chosen_text
                                    st.session_state["sg_brushup_per_block"][bi]["original"] = chosen_text
                                    st.rerun()
                                else:
                                    st.warning(f"ブロック{bi+1}が見つかりませんでした。")
                else:
                    # 通常ブロック（変更なし）
                    st.markdown(
                        f'<div style="padding:8px 14px;margin:2px 0;font-size:0.86rem;'
                        f'color:#374151;line-height:1.7;white-space:pre-wrap;">{para_text}</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown("<br>", unsafe_allow_html=True)

            # 全ブロック差し替え済みなら「台本完了」ボタンを表示
            all_applied = all(b.get("applied", False) for b in per_block)
            if all_applied:
                st.markdown(
                    '<div style="background:linear-gradient(135deg,#F0FDF4,#ECFDF5);'
                    'border:1px solid #A7F3D0;border-radius:12px;padding:14px 18px;margin-bottom:12px;">'
                    '<div style="font-weight:700;color:#065F46;font-size:0.95rem;">🎉 すべての差し替えが完了しました</div>'
                    '<div style="color:#047857;font-size:0.82rem;margin-top:4px;">'
                    '「台本完了」を押すと、修正内容をAIが分析してNGパターンと改善ルールを学習します。次回以降の生成に自動反映されます。</div></div>',
                    unsafe_allow_html=True,
                )
                if st.button("🎓 台本完了 — 学習データとして保存", type="primary",
                             key="sg_brushup_done", use_container_width=True):
                    with st.spinner("修正内容を分析・学習中..."):
                        try:
                            # 差し替えペアを収集
                            replacements = [
                                {"original_before": b["original_before"], "chosen": b.get("chosen", b["original"])}
                                for b in per_block if b.get("applied")
                            ]
                            # NGパターンを抽出して保存
                            from script_crew import analyze_brushup_replacements
                            ng_patterns = analyze_brushup_replacements(replacements, script_type, model_id)
                            if ng_patterns:
                                from memory_manager import _load_history, _save_history, _type_data
                                history = _load_history()
                                td = _type_data(history, script_type)
                                for p in ng_patterns:
                                    if p not in td["bad_patterns"]:
                                        td["bad_patterns"].append(p)
                                td["bad_patterns"] = td["bad_patterns"][-30:]
                                _save_history(history)

                            # 改善ルールも統合（edit_improvements）
                            from script_crew import analyze_edit_improvements, consolidate_improvement_rules
                            from memory_manager import get_edit_improvements, save_edit_improvements
                            combined_before = "\n\n".join(r["original_before"] for r in replacements)
                            combined_after  = "\n\n".join(r["chosen"] for r in replacements)
                            new_rules = analyze_edit_improvements(combined_before, combined_after, script_type, model_id)
                            if new_rules:
                                current_rules = get_edit_improvements(script_type)
                                consolidated = consolidate_improvement_rules(current_rules, new_rules, script_type, model_id)
                                save_edit_improvements(consolidated, script_type)

                            # 完成台本を"good"として保存
                            from memory_manager import save_script, record_theme_used
                            theme = (st.session_state.sg_selected_themes[0]
                                     if st.session_state.sg_selected_themes else "不明")
                            angle_key = st.session_state.sg_current_angle[0]
                            save_script(script=st.session_state.sg_edited_draft, rating="good",
                                        theme=theme, script_type=script_type, angle=angle_key)
                            record_theme_used(theme=theme, script_type=script_type, angle=angle_key)

                            st.session_state["sg_brushup_learned_ng"] = ng_patterns
                        except Exception as e:
                            st.error(f"学習エラー: {e}")

                    # 結果を表示してブラッシュアップ状態をクリア
                    ng_list = st.session_state.pop("sg_brushup_learned_ng", [])
                    st.session_state["sg_brushup_per_block"] = []
                    st.session_state["sg_brushup_candidates"] = []
                    st.session_state["sg_brushup_selected_blocks"] = []
                    st.session_state["sg_brushup_checked"] = []
                    if ng_list:
                        ng_html = "".join(
                            f'<div style="display:flex;gap:8px;margin-bottom:4px;">'
                            f'<span style="color:#DC2626;flex-shrink:0;">✕</span>'
                            f'<span style="font-size:0.83rem;color:#991B1B;">{p}</span></div>'
                            for p in ng_list
                        )
                        st.markdown(
                            f'<div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:12px;'
                            f'padding:14px 18px;margin-top:12px;">'
                            f'<div style="font-weight:700;color:#991B1B;margin-bottom:8px;">📚 学習したNGパターン（次回から回避）</div>'
                            f'{ng_html}</div>',
                            unsafe_allow_html=True,
                        )
                    st.success("✅ 学習完了！次回の台本生成に反映されます。")
                    st.rerun()

            col_cancel, _ = st.columns([2, 5])
            with col_cancel:
                if st.button("✕ キャンセル・やり直す", key="sg_brushup_clear"):
                    st.session_state["sg_brushup_per_block"] = []
                    st.session_state["sg_brushup_candidates"] = []
                    st.session_state["sg_brushup_selected_blocks"] = []
                    st.session_state["sg_brushup_checked"] = []
                    st.rerun()

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
