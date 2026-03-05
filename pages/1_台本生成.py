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

# Streamlit Community Cloud の Secrets にも対応
try:
    for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "SERPER_API_KEY", "GOOGLE_API_KEY", "XAI_API_KEY"]:
        if key in st.secrets and not os.getenv(key):
            os.environ[key] = st.secrets[key]
except Exception:
    pass

st.set_page_config(
    page_title="台本生成システム",
    page_icon="📝",
    layout="wide",
)

# ─── Session State 初期化 ────────────────────────────────────────────
def _init():
    defaults = {
        "sg_step": 0,
        "sg_script_type": "youtube",
        "sg_keyword": "",
        "sg_themes": [],
        "sg_selected_themes": [],
        "sg_ideas": [],
        "sg_selected_ideas": [],
        "sg_draft": "",
        "sg_edited_draft": "",
        "sg_final_result": "",
        "sg_titles": "",
        "sg_current_angle": ("science", "科学・データ根拠型"),
        "sg_saved": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()


def reset_all():
    """全ステートをリセットして最初に戻る"""
    for k in list(st.session_state.keys()):
        if k.startswith("sg_"):
            del st.session_state[k]
    _init()


# ─── ヘッダー + ステップ表示 ─────────────────────────────────────────
st.title("📝 台本生成システム")

STEP_LABELS = ["タイプ選択", "テーマ選択", "アイデア選択", "台本確認", "完成・評価"]
header_cols = st.columns(len(STEP_LABELS))
for i, (col, label) in enumerate(zip(header_cols, STEP_LABELS)):
    with col:
        cur = st.session_state.sg_step
        if i < cur:
            st.markdown(f"✅ ~~{label}~~")
        elif i == cur:
            st.markdown(f"▶️ **{label}**")
        else:
            st.markdown(f"⬜ {label}")

st.divider()

step = st.session_state.sg_step


# ════════════════════════════════════════════════════════════════════
# Step 0: タイプ選択 + キーワード入力
# ════════════════════════════════════════════════════════════════════
if step == 0:
    st.subheader("Step 1: 台本のタイプとキーワードを入力")

    col_type, col_stats = st.columns([2, 1])

    with col_type:
        script_type = st.radio(
            "台本タイプを選択",
            options=["youtube", "reel"],
            format_func=lambda x: (
                "📹 YouTube台本（4500〜5000文字）" if x == "youtube"
                else "📱 リール台本（700〜800文字）"
            ),
            index=0 if st.session_state.sg_script_type == "youtube" else 1,
        )

        keyword = st.text_input(
            "テーマのキーワード",
            value=st.session_state.sg_keyword,
            placeholder="例：糖質制限、筋トレ、更年期、有酸素運動",
        )
        st.caption("💡 Serperで最新トレンドを自動検索し、フレッシュなテーマを提案します")

    with col_stats:
        try:
            from memory_manager import get_stats, get_next_angle
            stats = get_stats()
            angle_key, angle_name = get_next_angle()
            st.info(
                f"**メモリ統計**\n\n"
                f"生成済み: {stats.get('total_generated', 0)}本\n\n"
                f"👍 好評: {stats.get('good_count', 0)}本\n\n"
                f"👎 悪評: {stats.get('bad_count', 0)}本\n\n"
                f"---\n\n**次のアングル**\n\n{angle_name}"
            )
        except Exception:
            st.info("📊 まだデータなし\n\n使うたびに学習されます")

    st.divider()
    if st.button(
        "テーマを20個生成 →",
        type="primary",
        disabled=not keyword.strip(),
        use_container_width=False,
    ):
        st.session_state.sg_script_type = script_type
        st.session_state.sg_keyword = keyword

        # アングル取得（メモリから）
        try:
            from memory_manager import get_used_themes, get_next_angle
            used_themes = get_used_themes()
            angle_key, angle_name = get_next_angle()
        except Exception:
            used_themes = []
            angle_key, angle_name = "science", "科学・データ根拠型"

        st.session_state.sg_current_angle = (angle_key, angle_name)

        with st.spinner(f"Serperで「{keyword}」のトレンドを検索中..."):
            try:
                from script_crew import get_trends
                trends = get_trends(keyword)
            except Exception:
                trends = []

        with st.spinner(f"テーマ候補を20個生成中... （アングル：{angle_name}）"):
            try:
                from script_crew import generate_themes
                themes = generate_themes(
                    script_type=script_type,
                    keyword=keyword,
                    used_themes=used_themes,
                    trends=trends,
                    angle_name=angle_name,
                )
                st.session_state.sg_themes = themes
                st.session_state.sg_step = 1
                st.rerun()
            except Exception as e:
                import traceback
                st.error(f"エラーが発生しました:\n{e}\n\n{traceback.format_exc()}")


# ════════════════════════════════════════════════════════════════════
# Step 1: テーマ候補20個 → 1〜3個選択
# ════════════════════════════════════════════════════════════════════
elif step == 1:
    angle_name = st.session_state.sg_current_angle[1]
    st.subheader("Step 2: テーマを1〜3個選んでください")
    st.caption(f"アングル（切り口）: **{angle_name}** ｜ キーワード: **{st.session_state.sg_keyword}**")

    themes = st.session_state.sg_themes

    if not themes:
        st.error("テーマ生成に失敗しました。戻って再試行してください。")
    else:
        selected = st.multiselect(
            "テーマを1〜3個選択（複数選択可）",
            options=themes,
            default=st.session_state.sg_selected_themes or [],
            max_selections=3,
            placeholder="クリックして選択...",
        )

        col_back, col_next = st.columns([1, 3])
        with col_back:
            if st.button("← 戻る"):
                st.session_state.sg_step = 0
                st.rerun()
        with col_next:
            if st.button(
                "アイデア20個を生成 →",
                type="primary",
                disabled=len(selected) == 0,
            ):
                st.session_state.sg_selected_themes = selected
                angle_name = st.session_state.sg_current_angle[1]

                try:
                    from memory_manager import get_good_elements
                    good_elements = get_good_elements()
                except Exception:
                    good_elements = []

                with st.spinner(f"コンテンツアイデアを20個生成中..."):
                    try:
                        from script_crew import generate_ideas
                        ideas = generate_ideas(
                            script_type=st.session_state.sg_script_type,
                            selected_themes=selected,
                            angle_name=angle_name,
                            good_elements=good_elements,
                        )
                        st.session_state.sg_ideas = ideas
                        st.session_state.sg_step = 2
                        st.rerun()
                    except Exception as e:
                        import traceback
                        st.error(f"エラー:\n{e}\n\n{traceback.format_exc()}")


# ════════════════════════════════════════════════════════════════════
# Step 2: アイデア20個 → 3個選択
# ════════════════════════════════════════════════════════════════════
elif step == 2:
    themes_str = " / ".join(st.session_state.sg_selected_themes)
    st.subheader("Step 3: 使いたいアイデアを3個選んでください")
    st.caption(f"テーマ: **{themes_str}**")

    ideas = st.session_state.sg_ideas

    if not ideas:
        st.error("アイデア生成に失敗しました。戻って再試行してください。")
    else:
        selected_ideas = st.multiselect(
            "アイデアを3個選択",
            options=ideas,
            default=st.session_state.sg_selected_ideas or [],
            max_selections=3,
            placeholder="クリックして選択...",
        )

        col_back, col_next = st.columns([1, 3])
        with col_back:
            if st.button("← 戻る"):
                st.session_state.sg_step = 1
                st.rerun()
        with col_next:
            char_range = "4500〜5000文字" if st.session_state.sg_script_type == "youtube" else "700〜800文字"
            if st.button(
                f"台本ドラフトを生成 → （{char_range}）",
                type="primary",
                disabled=len(selected_ideas) == 0,
            ):
                st.session_state.sg_selected_ideas = selected_ideas

                try:
                    from memory_manager import get_good_elements, get_bad_patterns, get_reference_scripts
                    good_elements = get_good_elements()
                    bad_patterns = get_bad_patterns()
                    ref_scripts = get_reference_scripts(st.session_state.sg_script_type)
                except Exception:
                    good_elements = []
                    bad_patterns = []
                    ref_scripts = []

                with st.spinner(f"台本ドラフトを生成中... ({char_range}) しばらくお待ちください"):
                    try:
                        from script_crew import generate_draft
                        draft = generate_draft(
                            script_type=st.session_state.sg_script_type,
                            selected_themes=st.session_state.sg_selected_themes,
                            selected_ideas=selected_ideas,
                            good_elements=good_elements,
                            bad_patterns=bad_patterns,
                            ref_scripts=ref_scripts,
                        )
                        st.session_state.sg_draft = draft
                        st.session_state.sg_edited_draft = draft
                        st.session_state.sg_step = 3
                        st.rerun()
                    except Exception as e:
                        import traceback
                        st.error(f"エラー:\n{e}\n\n{traceback.format_exc()}")


# ════════════════════════════════════════════════════════════════════
# Step 3: 台本確認・編集
# ════════════════════════════════════════════════════════════════════
elif step == 3:
    st.subheader("Step 4: 台本を確認・編集してください")

    draft = st.session_state.sg_edited_draft or st.session_state.sg_draft

    edited = st.text_area(
        "台本（直接編集できます）",
        value=draft,
        height=520,
    )

    # 文字数チェック
    char_count = len(edited)
    script_type = st.session_state.sg_script_type
    target_min, target_max = (4500, 5000) if script_type == "youtube" else (700, 800)

    if char_count < target_min:
        st.warning(f"文字数: **{char_count}文字** ｜ 目標: {target_min}〜{target_max}文字（あと **{target_min - char_count}文字** 必要）")
    elif char_count > target_max:
        st.warning(f"文字数: **{char_count}文字** ｜ 目標: {target_min}〜{target_max}文字（**{char_count - target_max}文字** オーバー）")
    else:
        st.success(f"文字数: **{char_count}文字** ｜ 目標範囲内 ({target_min}〜{target_max}文字) ✅")

    col_back, col_fc = st.columns([1, 3])
    with col_back:
        if st.button("← 戻る"):
            st.session_state.sg_step = 2
            st.rerun()
    with col_fc:
        if st.button("ファクトチェック → 完成 →", type="primary"):
            st.session_state.sg_edited_draft = edited
            st.session_state.sg_step = 4
            st.rerun()


# ════════════════════════════════════════════════════════════════════
# Step 4: ファクトチェック + タイトル生成 + 評価
# ════════════════════════════════════════════════════════════════════
elif step == 4:
    st.subheader("Step 5: ファクトチェック・タイトル生成・評価")

    draft = st.session_state.sg_edited_draft
    script_type = st.session_state.sg_script_type

    # ── まだ実行していない場合 ────────────────────────────────────
    if not st.session_state.sg_final_result:
        st.info("ファクトチェックとタイトル生成を同時実行しています。完了まで2〜3分かかります。")

        result_holder = {}
        log_queue_obj: queue.Queue = queue.Queue()

        class _StdoutCapture(StringIO):
            def write(self, text: str):
                stripped = text.strip()
                if stripped:
                    log_queue_obj.put(stripped)
                return super().write(text)

        def _run_factcheck():
            old_stdout = sys.stdout
            sys.stdout = _StdoutCapture()
            try:
                from crew import FactCheckCrew
                result = FactCheckCrew().run(text=draft)
                result_holder["result"] = str(result)
            except Exception as e:
                import traceback
                result_holder["error"] = str(e) + "\n\n" + traceback.format_exc()
            finally:
                sys.stdout = old_stdout

        def _run_titles():
            try:
                from script_crew import generate_titles
                titles = generate_titles(draft=draft, script_type=script_type)
                result_holder["titles"] = titles
            except Exception as e:
                result_holder["titles"] = f"（タイトル生成エラー: {e}）"

        thread_fc = threading.Thread(target=_run_factcheck, daemon=True)
        thread_titles = threading.Thread(target=_run_titles, daemon=True)
        thread_fc.start()
        thread_titles.start()

        status_area = st.empty()
        log_area = st.empty()
        log_lines = []

        while thread_fc.is_alive() or thread_titles.is_alive():
            # ログ収集（ファクトチェックのverbose出力）
            while not log_queue_obj.empty():
                line = log_queue_obj.get()
                if line.startswith(("│", "╭", "╰", "╮")):
                    inner = line.strip("│╭╰╮─ \t")
                    if inner:
                        log_lines.append(inner)
                else:
                    log_lines.append(line)
                log_area.code("\n".join(log_lines[-25:]), language=None)

            fc_status = "⚙️ 処理中" if thread_fc.is_alive() else "✅ 完了"
            ti_status = "⚙️ 処理中" if thread_titles.is_alive() else "✅ 完了"
            status_area.info(
                f"ファクトチェック: **{fc_status}** ｜ タイトル生成: **{ti_status}**"
            )
            time.sleep(1)

        thread_fc.join()
        thread_titles.join()
        log_area.empty()
        status_area.empty()

        if "error" in result_holder:
            st.error(f"ファクトチェックエラー:\n{result_holder['error']}")
            col_back2, _ = st.columns([1, 3])
            with col_back2:
                if st.button("← 戻る"):
                    st.session_state.sg_step = 3
                    st.rerun()
        else:
            st.session_state.sg_final_result = result_holder.get("result", "")
            st.session_state.sg_titles = result_holder.get("titles", "")
            st.rerun()

    # ── 結果表示 ──────────────────────────────────────────────────
    else:
        final_script = st.session_state.sg_edited_draft
        final_result = st.session_state.sg_final_result
        titles = st.session_state.sg_titles

        # タイトル・サムネ案
        if titles:
            with st.expander("🎯 タイトル候補・サムネイルテキスト案", expanded=True):
                st.markdown(titles)

        # ファクトチェック結果
        with st.expander("📊 ファクトチェック結果", expanded=False):
            for line in final_result.split("\n"):
                if "✅" in line:
                    st.success(line)
                elif "❌" in line:
                    st.error(line)
                elif "⚠️" in line:
                    st.warning(line)
                elif line.startswith("#"):
                    st.markdown(line)
                else:
                    if line.strip():
                        st.write(line)

        st.divider()

        # 完成台本
        st.subheader("完成台本")
        char_count = len(final_script)
        st.caption(f"文字数: {char_count}文字")
        st.text_area("完成台本", value=final_script, height=400, disabled=True)

        # ダウンロードボタン
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(
                "📥 台本をダウンロード",
                data=final_script,
                file_name=f"script_{script_type}_{ts}.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with col_dl2:
            combined = (
                f"=== 完成台本 ===\n{final_script}\n\n"
                f"=== タイトル・サムネイル案 ===\n{titles}\n\n"
                f"=== ファクトチェック結果 ===\n{final_result}"
            )
            st.download_button(
                "📥 全データをダウンロード",
                data=combined,
                file_name=f"script_full_{script_type}_{ts}.txt",
                mime="text/plain",
                use_container_width=True,
            )

        st.divider()

        # 評価ボタン
        if not st.session_state.sg_saved:
            st.subheader("この台本を評価してください")
            st.caption("評価はメモリに保存され、次回の生成品質向上に使われます")

            theme = (st.session_state.sg_selected_themes[0]
                     if st.session_state.sg_selected_themes else "不明")
            angle_key = st.session_state.sg_current_angle[0]

            col_good, col_bad = st.columns(2)
            with col_good:
                if st.button("👍 良い台本だった", type="primary", use_container_width=True):
                    try:
                        from memory_manager import save_script, record_theme_used
                        save_script(
                            script=final_script,
                            rating="good",
                            theme=theme,
                            script_type=script_type,
                            angle=angle_key,
                        )
                        record_theme_used(
                            theme=theme,
                            script_type=script_type,
                            angle=angle_key,
                        )
                        st.session_state.sg_saved = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"保存エラー: {e}")
            with col_bad:
                if st.button("👎 改善が必要", use_container_width=True):
                    try:
                        from memory_manager import save_script, record_theme_used
                        save_script(
                            script=final_script,
                            rating="bad",
                            theme=theme,
                            script_type=script_type,
                            angle=angle_key,
                        )
                        record_theme_used(
                            theme=theme,
                            script_type=script_type,
                            angle=angle_key,
                        )
                        st.session_state.sg_saved = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"保存エラー: {e}")
        else:
            st.success("✅ 評価を保存しました！次回の台本生成に反映されます。")

        st.divider()
        if st.button("🔄 新しい台本を生成する", type="secondary", use_container_width=False):
            reset_all()
            st.rerun()


# ─── フッター（リセットボタン） ──────────────────────────────────────
if step > 0:
    st.divider()
    if st.button("↩️ 最初からやり直す", type="secondary"):
        reset_all()
        st.rerun()
