import streamlit as st
import sys
import datetime
import queue
import threading
from io import StringIO
from dotenv import load_dotenv

load_dotenv(override=True)

# ─── ページ設定 ───────────────────────────────────────────────
st.set_page_config(
    page_title="マルチAI ファクトチェック",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 マルチAI ファクトチェックシステム")
st.caption("Claude × GPT-4o × Gemini が独立して事実を検証します")
st.divider()

# ─── 入力エリア ───────────────────────────────────────────────
st.subheader("📝 検証する文章を入力")

tab_paste, tab_file = st.tabs(["テキストを貼り付ける", "ファイルを読み込む"])

text_input = ""

with tab_paste:
    text_input_area = st.text_area(
        "文章を貼り付け",
        height=250,
        placeholder="検証したい文章をここに貼り付けてください...",
        label_visibility="collapsed",
    )
    if text_input_area:
        text_input = text_input_area

with tab_file:
    uploaded_file = st.file_uploader("テキストファイル（.txt）", type=["txt"])
    if uploaded_file:
        text_input = uploaded_file.read().decode("utf-8")
        st.success(f"読み込み完了: {len(text_input)}文字")
        st.text_area(
            "プレビュー",
            text_input[:500] + ("..." if len(text_input) > 500 else ""),
            height=120,
            disabled=True,
        )

if text_input:
    st.caption(f"文字数: {len(text_input)}文字")

st.divider()

# ─── 実行ボタン ───────────────────────────────────────────────
col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    run_button = st.button(
        "🚀 ファクトチェック開始",
        type="primary",
        use_container_width=True,
        disabled=not bool(text_input.strip()),
    )

# ─── 実行 ────────────────────────────────────────────────────
if run_button and text_input.strip():

    result_holder = {}
    log_queue: queue.Queue = queue.Queue()

    class _StdoutCapture(StringIO):
        """CrewAI の verbose 出力をキューに流す"""
        def write(self, text: str):
            stripped = text.strip()
            if stripped:
                log_queue.put(stripped)
            return super().write(text)

    def _run_crew():
        old_stdout = sys.stdout
        sys.stdout = _StdoutCapture()
        try:
            from crew import FactCheckCrew
            result = FactCheckCrew().run(text=text_input)
            result_holder["result"] = result
        except Exception as e:
            import traceback
            result_holder["error"] = str(e) + "\n\n" + traceback.format_exc()
        finally:
            sys.stdout = old_stdout

    thread = threading.Thread(target=_run_crew, daemon=True)
    thread.start()

    # ─── 進捗表示 ────────────────────────────────────────────
    st.subheader("⚙️ 処理中...")

    steps = [
        ("📝", "主張を抽出中", "Claude Haiku"),
        ("🔍", "GPT-4oがファクトチェック中", "GPT-4o"),
        ("🌐", "Geminiが独立検証中", "Gemini 1.5 Pro"),
        ("✍️", "編集長が結果を統合中", "Claude Sonnet"),
    ]

    step_cols = st.columns(len(steps))
    step_placeholders = []
    for i, (emoji, label, model) in enumerate(steps):
        with step_cols[i]:
            p = st.empty()
            p.markdown(f"⬜ {emoji} **{label}**\n\n`{model}`")
            step_placeholders.append(p)

    log_area = st.empty()
    log_lines: list[str] = []

    import time
    current_step = 0
    STEP_INTERVAL = 25  # 秒（目安）
    step_start = time.time()

    while thread.is_alive():
        # ステップ進行（時間ベース）
        elapsed = time.time() - step_start
        if current_step < len(steps) - 1 and elapsed > STEP_INTERVAL:
            step_placeholders[current_step].markdown(
                f"✅ {steps[current_step][0]} **{steps[current_step][1]}**\n\n`{steps[current_step][2]}`"
            )
            current_step += 1
            step_start = time.time()

        # ログ収集
        while not log_queue.empty():
            line = log_queue.get()
            # CrewAI のボックス枠など装飾行を除外して読みやすく
            if line.startswith("│") or line.startswith("╭") or line.startswith("╰") or line.startswith("╮"):
                inner = line.strip("│╭╰╮─ \t")
                if inner:
                    log_lines.append(inner)
            else:
                log_lines.append(line)
            # 最新30行だけ表示
            display = log_lines[-30:]
            log_area.code("\n".join(display), language=None)

        time.sleep(1)

    thread.join()

    # 全ステップ完了マーク
    for i in range(len(steps)):
        step_placeholders[i].markdown(
            f"✅ {steps[i][0]} **{steps[i][1]}**\n\n`{steps[i][2]}`"
        )

    log_area.empty()

    # ─── 結果表示 ─────────────────────────────────────────────
    st.divider()

    if "error" in result_holder:
        st.error(f"エラーが発生しました:\n\n{result_holder['error']}")
    else:
        result_text = result_holder.get("result", "")
        st.subheader("📊 ファクトチェック結果")

        # ✅ ⚠️ ❌ が含まれる行をハイライト
        for line in result_text.split("\n"):
            if "✅" in line:
                st.success(line)
            elif "❌" in line:
                st.error(line)
            elif "⚠️" in line:
                st.warning(line)
            elif line.startswith("#"):
                st.markdown(line)
            else:
                st.write(line)

        st.divider()

        # ダウンロードボタン
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        col1, col2 = st.columns([1, 3])
        with col1:
            st.download_button(
                label="📥 結果をダウンロード",
                data=result_text,
                file_name=f"factcheck_{timestamp}.txt",
                mime="text/plain",
                use_container_width=True,
            )
