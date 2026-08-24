import os
from dotenv import load_dotenv
import streamlit as st
from openai import OpenAI

load_dotenv()

st.set_page_config(page_title="GPT-5.6 Luna", page_icon="💬", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

*, *::before, *::after { font-family: 'Inter', sans-serif !important; box-sizing: border-box; }

/* 背景 */
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {
    background: #0d0d1a !important;
}
[data-testid="stHeader"]           { background: transparent !important; }
[data-testid="stSidebar"]          { background: #080810 !important; }
[data-testid="stSidebarContent"]   { background: #080810 !important; }
.block-container {
    max-width: 720px !important;
    padding: 1.5rem 1rem 6rem !important;
    margin: 0 auto !important;
}

/* 全テキストを白に統一 */
*, p, span, div, label, h1, h2, h3, h4, li {
    color: #e2e8f0 !important;
}

/* チャットメッセージ全体 */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    padding: 4px 0 !important;
    gap: 10px !important;
}

/* ユーザーバブル */
[data-testid="stChatMessage"][data-testid*="user"] [data-testid="stMarkdownContainer"],
[data-testid="stChatMessage"]:has([aria-label="user avatar"]) [data-testid="stMarkdownContainer"] {
    background: #1e1b4b !important;
    border-radius: 18px 18px 4px 18px !important;
    padding: 12px 16px !important;
}

/* アシスタントバブル */
[data-testid="stChatMessage"]:has([aria-label="assistant avatar"]) [data-testid="stMarkdownContainer"] {
    background: #0f2027 !important;
    border-radius: 18px 18px 18px 4px !important;
    padding: 12px 16px !important;
}

/* マークダウン内テキスト */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span {
    color: #e2e8f0 !important;
    line-height: 1.75 !important;
    font-size: 15px !important;
}

/* アバターアイコン */
[data-testid="stChatMessage"] img,
[data-testid="stChatMessage"] svg {
    border-radius: 50% !important;
}

/* 入力欄 */
[data-testid="stChatInput"] {
    background: #13131f !important;
    border-top: 1px solid #1e1e38 !important;
}
[data-testid="stChatInput"] textarea {
    background: #1a1a2e !important;
    color: #e2e8f0 !important;
    border: 1px solid #2d2d50 !important;
    border-radius: 14px !important;
    font-size: 15px !important;
    padding: 12px 16px !important;
    caret-color: #a78bfa !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: #4b5563 !important; }
[data-testid="stChatInput"] textarea:focus {
    border-color: #4f46e5 !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(79,70,229,0.2) !important;
}

/* 送信ボタン */
[data-testid="stChatInput"] button {
    background: #4f46e5 !important;
    border-radius: 10px !important;
    color: white !important;
}

/* リセットボタン */
div[data-testid="stButton"] > button[kind="secondary"] {
    background: rgba(255,255,255,0.05) !important;
    color: #6b7280 !important;
    border: 1px solid #1f2937 !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    padding: 6px 16px !important;
    width: 100% !important;
}

/* 区切り線 */
hr { border-color: #1e1e38 !important; margin: 12px 0 !important; }

/* コストバッジ */
.cost-bar {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 8px 14px;
    background: rgba(255,255,255,0.03);
    border: 1px solid #1e1e38;
    border-radius: 10px;
    margin-bottom: 12px;
    flex-wrap: wrap;
}
.cost-item {
    font-size: 12px;
    color: #6b7280 !important;
}
.cost-item span {
    color: #a78bfa !important;
    font-weight: 600;
}

/* スピナー */
[data-testid="stSpinner"] { color: #a78bfa !important; }

/* ヘッダーエリア */
.chat-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4px;
    flex-wrap: wrap;
    gap: 8px;
}
.chat-title {
    font-size: 22px;
    font-weight: 700;
    background: linear-gradient(135deg, #e2d9f3, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.model-tag {
    font-size: 11px;
    color: #4b5563 !important;
    background: rgba(255,255,255,0.04);
    border: 1px solid #1e1e38;
    border-radius: 20px;
    padding: 3px 12px;
}

/* 空状態 */
.empty-chat {
    text-align: center;
    padding: 60px 0 40px;
    color: #1f2937 !important;
}
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-text { font-size: 14px; color: #374151 !important; }

/* スマホ対応 */
@media (max-width: 640px) {
    .block-container { padding: 1rem 0.5rem 5rem !important; }
    [data-testid="stMarkdownContainer"] p { font-size: 14px !important; }
    .chat-title { font-size: 18px !important; }
    .cost-item  { font-size: 11px !important; }
}
</style>
""", unsafe_allow_html=True)

# セッション初期化
if "messages"     not in st.session_state: st.session_state.messages     = []
if "total_tokens" not in st.session_state: st.session_state.total_tokens = {"input": 0, "output": 0}

# ── ヘッダー ──
col_title, col_reset = st.columns([4, 1])
with col_title:
    st.markdown("""
<div class="chat-header">
  <div class="chat-title">💬 GPT-5.6 Luna</div>
  <div class="model-tag">gpt-5.6-luna</div>
</div>
""", unsafe_allow_html=True)
with col_reset:
    st.markdown("<div style='padding-top:6px'>", unsafe_allow_html=True)
    if st.button("リセット", type="secondary", use_container_width=True):
        st.session_state.messages     = []
        st.session_state.total_tokens = {"input": 0, "output": 0}
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

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
  <div class="empty-text">GPT-5.6 Luna にメッセージを送ってみてください</div>
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
        with st.spinner("生成中..."):
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
