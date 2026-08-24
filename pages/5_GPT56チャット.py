import os
from dotenv import load_dotenv
import streamlit as st
from openai import OpenAI

load_dotenv()

st.set_page_config(page_title="GPT-5.6 Luna チャット", page_icon="💬", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
* { font-family: 'Inter', sans-serif !important; }
[data-testid="stAppViewContainer"] {
    background: #0a0a14;
}
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"] { background: #07070f !important; }
.block-container { max-width: 800px; padding-top: 2rem !important; }
h1, h2, h3, p, label { color: #e2e8f0 !important; }

/* 入力欄 */
[data-testid="stChatInput"] textarea {
    background: #1a1a2e !important;
    color: #e2e8f0 !important;
    border: 1px solid #2d2d4e !important;
    border-radius: 12px !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("## 💬 GPT-5.6 Luna")
st.markdown(
    "<p style='color:#4b5563; font-size:12px;'>モデル: gpt-5.6-luna　・　$0.20/1M input　$1.20/1M output</p>",
    unsafe_allow_html=True,
)

# セッション初期化
if "messages" not in st.session_state:
    st.session_state.messages = []
if "total_tokens" not in st.session_state:
    st.session_state.total_tokens = {"input": 0, "output": 0}

# リセットボタン
col1, col2 = st.columns([5, 1])
with col2:
    if st.button("リセット", type="secondary"):
        st.session_state.messages = []
        st.session_state.total_tokens = {"input": 0, "output": 0}
        st.rerun()

# コスト表示
total_input  = st.session_state.total_tokens["input"]
total_output = st.session_state.total_tokens["output"]
cost_usd = (total_input / 1_000_000 * 0.20) + (total_output / 1_000_000 * 1.20)
cost_jpy = cost_usd * 150
if total_input > 0:
    st.markdown(
        f"<p style='color:#374151; font-size:11px;'>今セッション：入力 {total_input:,} tokens　出力 {total_output:,} tokens　推定コスト 約{cost_jpy:.1f}円</p>",
        unsafe_allow_html=True,
    )

st.markdown("---")

# 過去メッセージ表示
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 入力
if prompt := st.chat_input("メッセージを入力..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    with st.chat_message("assistant"):
        with st.spinner(""):
            res = client.chat.completions.create(
                model="gpt-5.6-luna",
                messages=st.session_state.messages,
                max_tokens=4096,
            )
        reply = res.choices[0].message.content
        st.write(reply)

        # トークン集計
        usage = res.usage
        st.session_state.total_tokens["input"]  += usage.prompt_tokens
        st.session_state.total_tokens["output"] += usage.completion_tokens

    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()
