import os
from dotenv import load_dotenv
import streamlit as st
from openai import OpenAI

load_dotenv()

st.set_page_config(page_title="GPT-5.6 Luna", page_icon="💬", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

*, *::before, *::after {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    box-sizing: border-box;
}

/* ── 背景・全体 ── */
html, body,
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background: #ffffff !important;
}
[data-testid="stHeader"] { background: #ffffff !important; border-bottom: 1px solid #e5e7eb; }
[data-testid="stSidebar"]        { background: #f9fafb !important; }
[data-testid="stSidebarContent"] { background: #f9fafb !important; }

.block-container {
    max-width: 760px !important;
    padding: 1rem 1.5rem 7rem !important;
    margin: 0 auto !important;
    background: #ffffff !important;
}

/* ── メインエリアのテキスト（黒） ── */
[data-testid="stMain"] p,
[data-testid="stMain"] span,
[data-testid="stMain"] div,
[data-testid="stMain"] label,
[data-testid="stMain"] li,
[data-testid="stMain"] h1,
[data-testid="stMain"] h2,
[data-testid="stMain"] h3 { color: #111827 !important; }

/* ── サイドバーのテキスト（黒） ── */
[data-testid="stSidebar"] *,
[data-testid="stSidebarContent"] *,
[data-testid="stSidebarNav"] * {
    color: #374151 !important;
}
[data-testid="stSidebarNav"] [aria-selected="true"],
[data-testid="stSidebarNav"] [aria-selected="true"] * {
    color: #111827 !important;
    font-weight: 600 !important;
}

/* ── チャットメッセージ全体 ── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    padding: 8px 0 !important;
    gap: 12px !important;
    align-items: flex-start !important;
}

/* アバター非表示（スッキリさせる） */
[data-testid="stChatMessage"] [data-testid="chatAvatarIcon-user"],
[data-testid="stChatMessage"] [data-testid="chatAvatarIcon-assistant"] {
    display: none !important;
}

/* ユーザーメッセージ */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stMarkdownContainer"],
[data-testid="stChatMessage"]:has([aria-label="user avatar"])            [data-testid="stMarkdownContainer"] {
    background: #ede9fe !important;
    border-radius: 18px 18px 4px 18px !important;
    padding: 12px 16px !important;
    margin-left: auto !important;
    max-width: 80% !important;
    display: block !important;
}

/* アシスタントメッセージ（バブルなし・プレーン） */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"],
[data-testid="stChatMessage"]:has([aria-label="assistant avatar"])            [data-testid="stMarkdownContainer"] {
    background: transparent !important;
    padding: 4px 0 !important;
    max-width: 100% !important;
}

/* マークダウン内テキスト */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] strong {
    color: #111827 !important;
    font-size: 15px !important;
    line-height: 1.75 !important;
}
[data-testid="stMarkdownContainer"] strong { font-weight: 600 !important; }

/* ── 入力欄 ── */
[data-testid="stBottom"],
[data-testid="stBottomBlockContainer"],
[data-testid="stBottomBlockContainer"] > div {
    background: #ffffff !important;
    border-top: 1px solid #e5e7eb !important;
}
[data-testid="stChatInput"] {
    background: #ffffff !important;
}
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] > div > div {
    background: #f9fafb !important;
    border-radius: 14px !important;
    border: 1px solid #d1d5db !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: #111827 !important;
    font-size: 15px !important;
    padding: 12px 16px !important;
    caret-color: #6d28d9 !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: #9ca3af !important; }
[data-testid="stChatInput"] textarea:focus {
    outline: none !important;
    border-color: transparent !important;
    box-shadow: none !important;
}
[data-testid="stChatInput"] button {
    background: #6d28d9 !important;
    border-radius: 10px !important;
    color: white !important;
}

/* ── ボタン ── */
div[data-testid="stButton"] > button {
    background: #f3f4f6 !important;
    color: #6b7280 !important;
    border: 1px solid #e5e7eb !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    padding: 5px 16px !important;
    box-shadow: none !important;
    min-height: 34px !important;
}
div[data-testid="stButton"] > button:hover {
    background: #e5e7eb !important;
    color: #374151 !important;
}

/* ── 区切り線 ── */
hr { border-color: #f3f4f6 !important; margin: 8px 0 !important; }

/* ── コストバー ── */
.cost-bar {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 7px 14px;
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    margin-bottom: 8px;
    flex-wrap: wrap;
}
.cost-item { font-size: 12px; color: #9ca3af !important; }
.cost-item span { color: #6d28d9 !important; font-weight: 600; }

/* ── モデルタグ ── */
.model-tag {
    font-size: 11px;
    color: #9ca3af !important;
    background: #f3f4f6;
    border: 1px solid #e5e7eb;
    border-radius: 20px;
    padding: 3px 12px;
    display: inline-block;
    margin-bottom: 2px;
}

/* ── タイトル ── */
.chat-title {
    font-size: 20px;
    font-weight: 600;
    color: #111827 !important;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* ── 空状態 ── */
.empty-chat {
    text-align: center;
    padding: 80px 0 40px;
}
.empty-icon { font-size: 40px; margin-bottom: 10px; }
.empty-text { font-size: 14px; color: #9ca3af !important; }
.empty-hint { font-size: 12px; color: #d1d5db !important; margin-top: 6px; }

/* ── スマホ対応 ── */
@media (max-width: 640px) {
    .block-container { padding: 0.75rem 1rem 6rem !important; }
    [data-testid="stMarkdownContainer"] p { font-size: 14px !important; }
    .chat-title { font-size: 17px !important; }
}
</style>
""", unsafe_allow_html=True)

# セッション初期化
if "messages"     not in st.session_state: st.session_state.messages     = []
if "total_tokens" not in st.session_state: st.session_state.total_tokens = {"input": 0, "output": 0}

# ── サイドバー：リセットボタン ──
with st.sidebar:
    st.markdown("---")
    if st.button("🔄 会話をリセット", use_container_width=True):
        st.session_state.messages     = []
        st.session_state.total_tokens = {"input": 0, "output": 0}
        st.rerun()

# ── ヘッダー ──
st.markdown("""
<div style="display:flex;align-items:center;gap:10px;padding:4px 0 12px;">
  <span class="chat-title">💬 GPT-5.6 Luna</span>
  <span class="model-tag">gpt-5.6-luna</span>
</div>
""", unsafe_allow_html=True)

# ── コスト表示 ──
ti = st.session_state.total_tokens["input"]
to = st.session_state.total_tokens["output"]
if ti > 0:
    cost_jpy = ((ti / 1_000_000 * 0.20) + (to / 1_000_000 * 1.20)) * 150
    st.markdown(f"""
<div class="cost-bar">
  <div class="cost-item">入力 <span>{ti:,}</span> tokens</div>
  <div class="cost-item">出力 <span>{to:,}</span> tokens</div>
  <div class="cost-item">推定コスト <span>約{cost_jpy:.1f}円</span></div>
</div>
""", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ── メッセージ表示 ──
if not st.session_state.messages:
    st.markdown("""
<div class="empty-chat">
  <div class="empty-icon">💬</div>
  <div class="empty-text">GPT-5.6 Luna に何でも聞いてみてください</div>
  <div class="empty-hint">台本のブラッシュアップ・質問・相談など</div>
</div>
""", unsafe_allow_html=True)
else:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# ── 入力 ──
if prompt := st.chat_input("メッセージを入力..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    with st.chat_message("assistant"):
        with st.spinner(""):
            res = client.chat.completions.create(
                model="gpt-5.6-luna",
                messages=st.session_state.messages,
                max_tokens=4096,
            )
        reply = res.choices[0].message.content
        st.markdown(reply)
        usage = res.usage
        st.session_state.total_tokens["input"]  += usage.prompt_tokens
        st.session_state.total_tokens["output"] += usage.completion_tokens

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()
