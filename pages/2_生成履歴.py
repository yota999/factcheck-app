import os
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
    page_title="生成履歴",
    page_icon="📚",
    layout="wide",
)

st.title("📚 生成履歴")
st.caption("過去に生成・評価した台本の一覧です")

try:
    from memory_manager import get_all_scripts_for_history, get_rejected_themes, get_rejected_ideas
    scripts = get_all_scripts_for_history()
    rejected_themes = get_rejected_themes()
    rejected_ideas = get_rejected_ideas()
except Exception as e:
    st.error(f"データ読み込みエラー: {e}")
    st.stop()

# ─── フィルター ──────────────────────────────────────────────────────
col_f1, col_f2 = st.columns(2)
with col_f1:
    filter_rating = st.selectbox(
        "評価でフィルター",
        options=["すべて", "👍 好評のみ", "👎 悪評のみ"],
        index=0,
    )
with col_f2:
    filter_type = st.selectbox(
        "タイプでフィルター",
        options=["すべて", "YouTube", "リール"],
        index=0,
    )

filtered = scripts
if filter_rating == "👍 好評のみ":
    filtered = [s for s in filtered if s["rating"] == "good"]
elif filter_rating == "👎 悪評のみ":
    filtered = [s for s in filtered if s["rating"] == "bad"]
if filter_type == "YouTube":
    filtered = [s for s in filtered if s["script_type"] == "youtube"]
elif filter_type == "リール":
    filtered = [s for s in filtered if s["script_type"] == "reel"]

st.divider()

if not filtered:
    st.info("該当する台本がありません。台本生成ページで台本を作って評価すると、ここに記録されます。")
else:
    st.caption(f"**{len(filtered)}件**の台本が見つかりました")

    for script in filtered:
        rating_icon = "👍" if script["rating"] == "good" else "👎"
        type_label = "📹 YouTube" if script["script_type"] == "youtube" else "📱 リール"
        theme = script["theme"] or "（テーマ不明）"
        date = script["date"] or "日時不明"

        with st.expander(f"{rating_icon} {type_label} ｜ {theme} ｜ {date}"):
            try:
                with open(script["path"], encoding="utf-8") as f:
                    content = f.read()
                # メタ行をスキップして本文だけ表示
                lines = content.split("\n")
                body_lines = [l for l in lines if not l.startswith("#")]
                body = "\n".join(body_lines).strip()
                char_count = len(body)
                st.caption(f"文字数: {char_count}文字 ｜ アングル: {script.get('angle', '不明')}")
                st.text_area(
                    "台本本文",
                    value=body,
                    height=300,
                    disabled=True,
                    key=f"hist_{script['filename']}",
                )
                st.download_button(
                    "📥 この台本をダウンロード",
                    data=body,
                    file_name=script["filename"],
                    mime="text/plain",
                    key=f"dl_{script['filename']}",
                )
            except Exception as e:
                st.error(f"ファイル読み込みエラー: {e}")

# ─── NGリスト確認 ────────────────────────────────────────────────────
st.divider()
st.subheader("🚫 NGリスト")

col_ng1, col_ng2 = st.columns(2)
with col_ng1:
    st.markdown("**NGテーマ一覧**")
    if rejected_themes:
        for t in rejected_themes[-20:]:
            st.markdown(f"- {t}")
    else:
        st.caption("まだNGテーマはありません")

with col_ng2:
    st.markdown("**NGアイデア一覧**")
    if rejected_ideas:
        for i in rejected_ideas[-20:]:
            st.markdown(f"- {i}")
    else:
        st.caption("まだNGアイデアはありません")
