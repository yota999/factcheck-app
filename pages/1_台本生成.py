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
        "sg_selected_themes": [],  # 互換性のため残す（空リスト）
        "sg_ideas": [],
        "sg_selected_ideas": [],   # 互換性のため残す（空リスト）
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
        # 元となる文章（ソーステキスト）
        "sg_source_text": "",
        # 4本並列生成・選択・反復編集ループ
        "sg_four_drafts": [],        # 4本の生成結果
        "sg_current_draft": "",      # 選択後の作業台本
        "sg_edit_count": 0,
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
  <p>素材テキストを入力するだけで、4つのAIが並列で台本を生成します</p>
</div>
""", unsafe_allow_html=True)


# ─── ステッププログレス ───────────────────────────────────────────────
# sg_step: 1=素材入力, 3=生成・編集, 4=完成
STEP_MAP = {1: 0, 3: 1, 4: 2}
STEP_LABELS = ["素材入力", "生成・編集", "完成"]

def render_steps():
    cur_step = st.session_state.sg_step
    cur = STEP_MAP.get(cur_step, 0)
    parts = []
    for i, label in enumerate(STEP_LABELS):
        if i < cur:
            cls = "step-done"; num_html = "✓"
        elif i == cur:
            cls = "step-active"; num_html = str(i + 1)
        else:
            cls = "step-pending"; num_html = str(i + 1)
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

step = st.session_state.sg_step

# ステッププログレスはStep 0（タイプ選択）以外で表示
if step != 0:
    render_steps()


# ════════════════════════════════════════════════════════════════════
# Step 0: タイプ選択
# ════════════════════════════════════════════════════════════════════
if step == 0:
    st.markdown('<div class="section-header">台本のタイプを選択してください</div>', unsafe_allow_html=True)

    col_yt, col_rl = st.columns(2)

    with col_yt:
        st.markdown('''<div class="type-card">
<div class="type-card-icon">📺</div>
<div class="type-card-title">YouTube 台本</div>
<div class="type-card-desc">長尺動画向けのしっかりした構成<br>解説・教育系コンテンツに最適</div>
<div class="type-card-badge">4,500〜5,000 文字</div>
</div>''', unsafe_allow_html=True)
        if st.button("📺 YouTube を選択", use_container_width=True, type="primary", key="sel_yt"):
            st.session_state.sg_script_type = "youtube"
            try:
                from memory_manager import get_next_angle, get_next_ai
                angle_key, angle_name = get_next_angle("youtube")
                model_id, model_name = get_next_ai("youtube")
            except Exception:
                angle_key, angle_name = "science", "科学・データ根拠型"
                model_id, model_name = "anthropic/claude-sonnet-4-6", "Claude Sonnet 4.6"
            st.session_state.sg_current_angle = (angle_key, angle_name)
            st.session_state.sg_current_ai = (model_id, model_name)
            st.session_state.sg_step = 1
            st.rerun()

    with col_rl:
        st.markdown('''<div class="type-card">
<div class="type-card-icon">📱</div>
<div class="type-card-title">リール台本</div>
<div class="type-card-desc">ショート動画向けのコンパクトな構成<br>インパクト重視・拡散向け</div>
<div class="type-card-badge">700〜800 文字</div>
</div>''', unsafe_allow_html=True)
        if st.button("📱 リール を選択", use_container_width=True, type="primary", key="sel_rl"):
            st.session_state.sg_script_type = "reel"
            try:
                from memory_manager import get_next_angle, get_next_ai
                angle_key, angle_name = get_next_angle("reel")
                model_id, model_name = get_next_ai("reel")
            except Exception:
                angle_key, angle_name = "science", "科学・データ根拠型"
                model_id, model_name = "anthropic/claude-sonnet-4-6", "Claude Sonnet 4.6"
            st.session_state.sg_current_angle = (angle_key, angle_name)
            st.session_state.sg_current_ai = (model_id, model_name)
            st.session_state.sg_step = 1
            st.rerun()


# ════════════════════════════════════════════════════════════════════
# Step 1: 元となる文章を入力
# ════════════════════════════════════════════════════════════════════
elif step == 1:
    script_type = st.session_state.sg_script_type
    type_label = "YouTube 台本" if script_type == "youtube" else "リール台本"

    st.markdown('<div class="section-header">Step 1 ／ 元となる文章を入力</div>', unsafe_allow_html=True)

    st.markdown("""
<div style="background:#F0F9FF;border:1px solid #BAE6FD;border-radius:12px;padding:14px 18px;margin-bottom:16px;">
<div style="font-weight:700;color:#0369A1;margin-bottom:6px;">📄 どんな文章でも台本の素材になります</div>
<div style="font-size:0.85rem;color:#0C4A6E;line-height:1.7;">
・ブログ記事・SNS投稿・メモ書き・論文の要約<br>
・参考にしたいYouTube動画の書き起こし<br>
・自分の体験談・アイデアのラフスケッチ<br>
・キーワードや箇条書きだけでもOK
</div>
</div>
""", unsafe_allow_html=True)

    source_text = st.text_area(
        "元となる文章を入力してください",
        value=st.session_state.get("sg_source_text", ""),
        height=300,
        placeholder="ここに文章を貼り付けるか、直接入力してください...\n\n例：\n・最近の研究で、睡眠不足がダイエットに悪影響を与えることが分かった\n・コルチゾールが増えると脂肪が蓄積しやすくなる\n・1日7時間以上の睡眠が理想的",
        key="sg_source_text_input",
    )

    col_bk, col_next = st.columns([1, 3])
    with col_bk:
        if st.button("← 戻る", key="step1_back"):
            st.session_state.sg_step = 0
            st.rerun()
    with col_next:
        if st.button("🚀 台本を生成する →", type="primary", use_container_width=True,
                     disabled=(len(source_text.strip()) < 10)):
            st.session_state.sg_source_text = source_text.strip()
            try:
                from memory_manager import get_next_angle, get_next_ai
                angle_key, angle_name = get_next_angle(script_type)
                model_id, model_name = get_next_ai(script_type)
            except Exception:
                angle_key, angle_name = "science", "科学・データ根拠型"
                model_id, model_name = "anthropic/claude-sonnet-4-6", "Claude Sonnet 4.6"
            st.session_state.sg_current_angle = (angle_key, angle_name)
            st.session_state.sg_current_ai = (model_id, model_name)
            st.session_state.sg_draft_variants = []
            st.session_state.sg_selected_variant_idx = 0
            st.session_state.sg_variant_error = ""
            st.session_state.sg_four_drafts = []
            st.session_state.sg_current_draft = ""
            st.session_state.sg_edit_count = 0
            st.session_state.sg_step = 3
            st.rerun()


# ════════════════════════════════════════════════════════════════════
# Step 3: 4本並列生成 → 選択 → 反復編集ループ
# ════════════════════════════════════════════════════════════════════
elif step == 3:
    script_type = st.session_state.sg_script_type
    model_id = st.session_state.sg_current_ai[0]

    st.markdown('<div class="section-header">Step 2 ／ 台本を生成・ブラッシュアップ</div>', unsafe_allow_html=True)

    four_drafts = st.session_state.get("sg_four_drafts", [])
    current_draft = st.session_state.get("sg_current_draft", "")

    # ── A) 4本未生成 → 並列生成 ──
    if not four_drafts:
        with st.spinner("Claude・GPT-4o・Gemini・Grokで4本を並列生成中...（1〜2分）"):
            try:
                from memory_manager import get_good_elements, get_bad_patterns, get_reference_scripts, get_edit_improvements
                good_elements = get_good_elements(script_type)
                bad_patterns = get_bad_patterns(script_type)
                ref_scripts = get_reference_scripts(script_type)
                edit_improvements = get_edit_improvements(script_type)
            except Exception:
                good_elements, bad_patterns, ref_scripts, edit_improvements = [], [], [], []
            try:
                from script_crew import generate_four_drafts
                drafts = generate_four_drafts(
                    script_type=script_type,
                    source_text=st.session_state.get("sg_source_text", ""),
                    good_elements=good_elements,
                    bad_patterns=bad_patterns,
                    ref_scripts=ref_scripts,
                    edit_improvements=edit_improvements,
                )
                st.session_state.sg_four_drafts = drafts
                st.rerun()
            except Exception as e:
                st.error(f"生成エラー: {e}")

    # ── B) 4本生成済み・未選択 → 選択カード ──
    elif not current_draft:
        st.markdown("### 🤖 4つのAIが生成した台本から1本を選んでください")
        st.markdown('<div style="font-size:0.85rem;color:#6B7280;margin-bottom:16px;">それぞれのAIが独自のアプローチで生成しました。気に入った台本を選んでブラッシュアップしていきます。</div>', unsafe_allow_html=True)

        AI_COLORS = {
            "Claude Sonnet 4.6": ("#7C3AED", "#F5F3FF", "#DDD6FE"),
            "GPT-4o":            ("#059669", "#ECFDF5", "#A7F3D0"),
            "Gemini 2.5 Pro":    ("#1D4ED8", "#EFF6FF", "#BFDBFE"),
            "Grok 3":            ("#374151", "#F3F4F6", "#D1D5DB"),
        }
        AI_ICONS = {
            "Claude Sonnet 4.6": "🟣",
            "GPT-4o":            "🟢",
            "Gemini 2.5 Pro":    "🔵",
            "Grok 3":            "⚫",
        }

        for i, d in enumerate(four_drafts):
            mname = d["model_name"]
            draft_text = d.get("draft") or ""
            if not draft_text.strip():
                continue
            txt_c, bg_c, border_c = AI_COLORS.get(mname, ("#4F46E5", "#EEF2FF", "#C7D2FE"))
            icon = AI_ICONS.get(mname, "🤖")
            draft_preview = draft_text[:200].replace("\n", " ") + "..."

            col_card, col_btn = st.columns([10, 2])
            with col_card:
                st.markdown(
                    f'<div style="background:{bg_c};border:1px solid {border_c};border-radius:12px;'
                    f'padding:14px 18px;margin-bottom:4px;">'
                    f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">'
                    f'<span style="font-size:1.2rem;">{icon}</span>'
                    f'<span style="font-weight:700;color:{txt_c};font-size:0.95rem;">{mname}</span>'
                    f'</div>'
                    f'<div style="font-size:0.82rem;color:#374151;line-height:1.65;">{draft_preview}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_btn:
                st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
                if st.button("この台本を選択", key=f"sel_draft_{i}", use_container_width=True, type="primary"):
                    st.session_state.sg_current_draft = draft_text
                    st.session_state.sg_edit_count = 0
                    st.rerun()
            st.markdown('<div style="margin-bottom:8px;"></div>', unsafe_allow_html=True)

        st.markdown("<br>")
        if st.button("🔄 4本を再生成する", key="regen_four"):
            st.session_state.sg_four_drafts = []
            st.rerun()
        if st.button("← 文章入力に戻る", key="s3_back_select"):
            st.session_state.sg_four_drafts = []
            st.session_state.sg_step = 1
            st.rerun()

    # ── C) 台本選択済み → 編集ループ ──
    else:
        edit_count = st.session_state.get("sg_edit_count", 0)

        # 編集回数バッジ
        if edit_count > 0:
            st.markdown(
                f'<div style="display:inline-block;background:#EEF2FF;border-radius:8px;'
                f'padding:4px 12px;font-size:0.82rem;color:#4338CA;font-weight:600;margin-bottom:12px;">'
                f'✏️ {edit_count}回修正済み</div>',
                unsafe_allow_html=True,
            )

        # 台本表示（編集可能なテキストエリア）
        edited = st.text_area(
            "生成された台本（直接編集もできます）",
            value=current_draft,
            height=500,
            key="sg_draft_display",
        )
        char_count = len(edited)
        # 文字数表示（目標900文字）
        target = 900
        if char_count < target - 50:
            st.caption(f"📝 {char_count}文字（目標 {target}文字前後）")
        elif char_count > target + 100:
            st.caption(f"📝 {char_count}文字（目標 {target}文字前後）")
        else:
            st.success(f"✓ {char_count}文字")

        # テキストエリアの手動編集を即時反映
        if edited != current_draft:
            st.session_state.sg_current_draft = edited

        st.markdown("---")
        st.markdown("### ✏️ 修正したい箇所を指定する")
        st.markdown('<div style="font-size:0.85rem;color:#6B7280;margin-bottom:8px;">修正したい文章を下にそのまま貼り付けて、どう直したいかを書いてください。</div>', unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        with col_a:
            target_text = st.text_area(
                "① 修正したい箇所（原文をそのままコピー）",
                height=150,
                key="sg_edit_target",
                placeholder="ここに修正したい文章をそのままコピーして貼り付けてください",
            )
        with col_b:
            edit_instruction = st.text_area(
                "② 修正の指示（どう変えたいか）",
                height=150,
                key="sg_edit_instruction",
                placeholder="例：「プレッシャー」という表現を「無力感」のニュアンスに変えてほしい",
            )

        col_apply, col_regen, col_next = st.columns([2, 1, 1])
        with col_apply:
            apply_disabled = not (target_text.strip() and edit_instruction.strip())
            if st.button("🔧 修正を適用する", type="primary", use_container_width=True,
                         disabled=apply_disabled, key="apply_edit"):
                with st.spinner("修正を適用・学習中..."):
                    try:
                        from script_crew import apply_partial_edit, analyze_edit_improvements, consolidate_improvement_rules
                        from memory_manager import get_edit_improvements, save_edit_improvements
                        # 修正を適用
                        new_draft = apply_partial_edit(
                            full_script=st.session_state.sg_current_draft,
                            target_text=target_text.strip(),
                            instruction=edit_instruction.strip(),
                            model=model_id,
                        )
                        original = st.session_state.sg_current_draft
                        st.session_state.sg_current_draft = new_draft
                        st.session_state.sg_edit_count = st.session_state.get("sg_edit_count", 0) + 1
                        # 修正差分を汎用ルールとして学習
                        new_rules = analyze_edit_improvements(original, new_draft, script_type, model_id)
                        if new_rules:
                            current_rules = get_edit_improvements(script_type)
                            consolidated = consolidate_improvement_rules(current_rules, new_rules, script_type, model_id)
                            save_edit_improvements(consolidated, script_type)
                            st.session_state["sg_last_learned_rules"] = consolidated
                        st.rerun()
                    except Exception as e:
                        st.error(f"修正エラー: {e}")

        with col_regen:
            if st.button("🔄 再生成", key="s3_regen", use_container_width=True):
                st.session_state.sg_four_drafts = []
                st.session_state.sg_current_draft = ""
                st.session_state.sg_edit_count = 0
                st.rerun()

        with col_next:
            if st.button("✅ 完成へ進む", key="s3_next", use_container_width=True):
                st.session_state.sg_edited_draft = st.session_state.sg_current_draft
                st.session_state.sg_titles = ""
                st.session_state.sg_step = 4
                st.rerun()

        # 学習済みルール表示
        last_rules = st.session_state.get("sg_last_learned_rules", [])
        if last_rules:
            st.markdown("---")
            st.markdown("**✨ 今回の修正から学習したルール**")
            for r in last_rules[-3:]:
                st.markdown(f'<div style="background:#ECFDF5;border-left:3px solid #10B981;padding:8px 12px;border-radius:4px;font-size:0.82rem;margin-bottom:4px;">{r}</div>', unsafe_allow_html=True)
            st.session_state["sg_last_learned_rules"] = []

        # 戻るボタン
        if st.button("← 台本選択に戻る", key="s3_back"):
            st.session_state.sg_current_draft = ""
            st.session_state.sg_edit_count = 0
            st.rerun()


# ════════════════════════════════════════════════════════════════════
# Step 4: タイトル生成 + 最終調整
# ════════════════════════════════════════════════════════════════════
elif step == 4:
    draft = st.session_state.sg_edited_draft
    script_type = st.session_state.sg_script_type
    model_id = st.session_state.sg_current_ai[0]
    _, ai_name = st.session_state.sg_current_ai

    st.markdown('<div class="section-header">Step 3 ／ 台本完成 ＆ 最終調整</div>', unsafe_allow_html=True)

    # ── 直前に学習したルールがあれば表示 ──────────────────────────
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
        st.session_state["sg_last_learned_rules"] = []

    # ── タイトル自動生成 ──────────────────────────────────────────
    titles = st.session_state.sg_titles
    if not titles:
        with st.spinner("タイトル候補を生成中..."):
            try:
                from script_crew import generate_titles
                titles = generate_titles(draft=draft, script_type=script_type, model=model_id)
                st.session_state.sg_titles = titles
                st.rerun()
            except Exception as e:
                st.warning(f"タイトル生成エラー: {e}")

    # ── タイトル候補カード ────────────────────────────────────────
    if titles:
        st.markdown("### 🎯 タイトル候補 ＆ サムネイルテキスト")
        col_t, col_s = st.columns([3, 2])
        with col_t:
            st.markdown(
                '<div style="background:white;border:1px solid #E5E7EB;border-radius:12px;'
                'padding:18px 20px;box-shadow:0 1px 4px rgba(0,0,0,.03);">'
                '<div style="font-size:0.78rem;color:#9CA3AF;margin-bottom:12px;font-weight:600;">'
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
                '<div style="font-size:0.78rem;color:#9CA3AF;margin-bottom:12px;font-weight:600;">'
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

    # ─ 完成台本 ＆ 最終調整 ──────────────────────────────────────
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
        height=840,
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
