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
/* ベースデザイン */
.main { background: #f0f2f6; }

/* カード */
.card {
    background: white;
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    margin-bottom: 16px;
}
.card-blue  { border-left: 4px solid #4F46E5; }
.card-green { border-left: 4px solid #059669; }
.card-amber { border-left: 4px solid #D97706; }
.card-red   { border-left: 4px solid #DC2626; }
.card-gray  { border-left: 4px solid #9CA3AF; }

/* ページタイトル */
.page-header {
    background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
    border-radius: 14px;
    padding: 24px 28px;
    color: white;
    margin-bottom: 20px;
}
.page-header h1 { margin: 0; font-size: 1.8rem; color: white; }
.page-header p  { margin: 4px 0 0; opacity: 0.85; font-size: 0.95rem; }

/* ステッププログレス */
.steps-wrap {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: white;
    border-radius: 12px;
    padding: 14px 20px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    margin-bottom: 20px;
    gap: 4px;
}
.step-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
    position: relative;
}
.step-num {
    width: 28px; height: 28px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.8rem; font-weight: 700;
    margin-bottom: 4px;
}
.step-label { font-size: 0.72rem; text-align: center; white-space: nowrap; }
.step-done  .step-num { background: #059669; color: white; }
.step-done  .step-label { color: #059669; }
.step-active .step-num { background: #4F46E5; color: white; box-shadow: 0 0 0 3px #C7D2FE; }
.step-active .step-label { color: #4F46E5; font-weight: 700; }
.step-pending .step-num { background: #E5E7EB; color: #9CA3AF; }
.step-pending .step-label { color: #9CA3AF; }
.step-connector {
    height: 2px; background: #E5E7EB; flex: 0 0 20px; margin-bottom: 20px;
}
.step-connector.done { background: #059669; }

/* タイプ選択カード */
.type-card {
    border: 2px solid #E5E7EB;
    border-radius: 12px;
    padding: 20px;
    cursor: pointer;
    transition: all 0.15s;
    text-align: center;
}
.type-card.selected { border-color: #4F46E5; background: #EEF2FF; }

/* バリアントカード（セクションビルダー） */
.variant-card {
    border: 2px solid #E5E7EB;
    border-radius: 10px;
    padding: 12px 14px;
    cursor: pointer;
    font-size: 0.83rem;
    line-height: 1.5;
    transition: border-color 0.15s, background 0.15s;
    margin-bottom: 8px;
    min-height: 80px;
}
.variant-card.active { border-color: #4F46E5; background: #EEF2FF; }
.variant-card:hover:not(.active) { border-color: #A5B4FC; }

/* ファクトチェックカード */
.fc-header {
    font-weight: 700;
    font-size: 0.95rem;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.verdict-good  { color: #059669; font-size: 1.1rem; }
.verdict-warn  { color: #D97706; font-size: 1.1rem; }
.verdict-bad   { color: #DC2626; font-size: 1.1rem; }
.verdict-unk   { color: #6B7280; font-size: 1.1rem; }

/* メモリ統計 */
.stat-box {
    background: #EEF2FF;
    border-radius: 10px;
    padding: 14px 16px;
    text-align: center;
}
.stat-num { font-size: 1.8rem; font-weight: 800; color: #4F46E5; }
.stat-lbl { font-size: 0.75rem; color: #6B7280; }

/* セクション区切り */
.section-header {
    background: linear-gradient(90deg, #EEF2FF 0%, transparent 100%);
    border-left: 3px solid #4F46E5;
    padding: 6px 12px;
    border-radius: 4px;
    font-weight: 700;
    font-size: 0.95rem;
    margin: 16px 0 10px;
    color: #3730A3;
}

/* ドロップダウン内テキスト折り返し */
[data-baseweb="menu"] li {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: unset !important;
    height: auto !important;
    padding-top: 10px !important;
    padding-bottom: 10px !important;
    line-height: 1.5 !important;
}
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
<div class="page-header">
  <h1>📝 台本生成システム</h1>
  <p>AI マルチエージェントが自動でテーマ → アイデア → 台本を生成</p>
</div>
""", unsafe_allow_html=True)


# ─── ステッププログレス ───────────────────────────────────────────────
STEP_LABELS = ["タイプ選択", "テーマ選択", "アイデア選択", "台本作成", "完成・評価"]

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
        f'<div class="steps-wrap">{"".join(parts)}</div>',
        unsafe_allow_html=True,
    )

render_steps()

step = st.session_state.sg_step


# ════════════════════════════════════════════════════════════════════
# Step 0: タイプ選択
# ════════════════════════════════════════════════════════════════════
if step == 0:
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown('<div class="section-header">Step 1 ／ 台本のタイプを選択</div>', unsafe_allow_html=True)

        script_type = st.radio(
            "台本タイプ",
            options=["youtube", "reel"],
            format_func=lambda x: "📺  YouTube台本（4500〜5000文字）" if x == "youtube" else "📱  リール台本（700〜800文字）",
            index=0 if st.session_state.sg_script_type == "youtube" else 1,
            label_visibility="collapsed",
        )
        st.caption("💡 Serper + YouTube Data API でトレンドを自動収集してテーマを提案します")

    with col_right:
        try:
            from memory_manager import get_stats, get_next_angle, get_next_ai
            stats = get_stats(script_type)
            angle_key, angle_name = get_next_angle(script_type)
            _, ai_name = get_next_ai(script_type)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f'<div class="stat-box"><div class="stat-num">{stats.get("total_generated",0)}</div><div class="stat-lbl">生成済み</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#059669">{stats.get("good_count",0)}</div><div class="stat-lbl">👍 好評</div></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="stat-box"><div class="stat-num" style="color:#DC2626">{stats.get("bad_count",0)}</div><div class="stat-lbl">👎 悪評</div></div>', unsafe_allow_html=True)
            st.caption(f"次のアングル: **{angle_name}** ／ 担当AI: **{ai_name}**")
        except Exception:
            st.info("📊 まだデータなし。使うたびに学習されます")

    st.divider()
    if st.button("テーマを自動生成 →", type="primary"):
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

        with st.spinner("📡 Serper + YouTube Data API でトレンドを収集中..."):
            try:
                from script_crew import fetch_all_trends
                trends, video_trends, youtube_trends = fetch_all_trends()
            except Exception:
                trends, video_trends, youtube_trends = [], [], []

        with st.spinner(f"🤖 {model_name} でテーマを20個生成中... （アングル：{angle_name}）"):
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
    st.caption(f"アングル: **{angle_name}** ｜ 担当AI: **{ai_name}**")

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

        with st.expander("🚫 気に入らないテーマをNG登録する（次回から表示されなくなります）"):
            ng_options = [t for t in themes if t not in selected]
            ng_selected = st.multiselect(
                "NG登録するテーマを選択", options=ng_options, default=[],
                key="sg_ng_theme_select", placeholder="気に入らないテーマを選ぶ...",
            )
            if st.button("🚫 NG登録", key="sg_ng_theme_btn", disabled=not ng_selected):
                try:
                    from memory_manager import add_rejected_themes
                    add_rejected_themes(ng_selected, st.session_state.sg_script_type)
                    st.success(f"✅ {len(ng_selected)}件をNG登録しました")
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
                    if new_t not in st.session_state.sg_themes:
                        st.session_state.sg_themes.append(new_t)
                    new_sel = list(selected)
                    if new_t not in new_sel:
                        new_sel.append(new_t)
                    st.session_state.sg_selected_themes = new_sel
                    st.rerun()
            if len(selected) >= 3:
                st.caption("（3個選択済みのため追加できません）")

        col_back, col_regen, col_next = st.columns([1, 1, 2])
        with col_back:
            if st.button("← 戻る"):
                st.session_state.sg_step = 0
                st.rerun()
        with col_regen:
            if st.button("🔄 再生成"):
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

                with st.spinner(f"🤖 {model_name} で再生成中..."):
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
            if st.button("アイデア20個を生成 →", type="primary", disabled=len(selected) == 0):
                st.session_state.sg_selected_themes = selected
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
                            selected_themes=selected, angle_name=angle_name,
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
    st.caption(f"テーマ: **{themes_str}** ｜ 担当AI: **{ai_name}**")

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

        with st.expander("🚫 気に入らないアイデアをNG登録する（次回から表示されなくなります）"):
            ng_options = [i for i in ideas if i not in selected_ideas]
            ng_selected = st.multiselect(
                "NG登録するアイデアを選択", options=ng_options, default=[],
                key="sg_ng_idea_select", placeholder="気に入らないアイデアを選ぶ...",
            )
            if st.button("🚫 NG登録", key="sg_ng_idea_btn", disabled=not ng_selected):
                try:
                    from memory_manager import add_rejected_ideas
                    add_rejected_ideas(ng_selected, st.session_state.sg_script_type)
                    st.success(f"✅ {len(ng_selected)}件をNG登録しました")
                except Exception as e:
                    st.error(f"保存エラー: {e}")

        with st.expander("✏️ リストにないアイデアを直接入力して追加"):
            c1, c2 = st.columns([4, 1])
            with c1:
                custom_idea = st.text_input("カスタムアイデア",
                    placeholder="例：夫に言われた一言で決意した体験談",
                    label_visibility="collapsed", key="sg_custom_idea_input")
            with c2:
                add_disabled = not custom_idea.strip() or len(selected_ideas) >= 3
                if st.button("＋追加", key="sg_add_idea", disabled=add_disabled):
                    new_idea = custom_idea.strip()
                    if new_idea not in st.session_state.sg_ideas:
                        st.session_state.sg_ideas.append(new_idea)
                    new_sel = list(selected_ideas)
                    if new_idea not in new_sel:
                        new_sel.append(new_idea)
                    st.session_state.sg_selected_ideas = new_sel
                    st.rerun()
            if len(selected_ideas) >= 3:
                st.caption("（3個選択済みのため追加できません）")

        col_back, col_regen, col_next = st.columns([1, 1, 2])
        with col_back:
            if st.button("← 戻る"):
                st.session_state.sg_step = 1
                st.rerun()
        with col_regen:
            if st.button("🔄 再生成"):
                model_id = st.session_state.sg_current_ai[0]
                angle_name = st.session_state.sg_current_angle[1]
                try:
                    from memory_manager import get_good_elements, get_rejected_ideas
                    good_elements = get_good_elements(st.session_state.sg_script_type)
                    rejected_ideas = get_rejected_ideas(st.session_state.sg_script_type)
                except Exception:
                    good_elements, rejected_ideas = [], []
                with st.spinner("🔄 アイデアを再生成中..."):
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
            if st.button("台本を生成 →", type="primary", disabled=len(selected_ideas) == 0):
                st.session_state.sg_selected_ideas = selected_ideas
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
    st.caption(f"担当AI: **{ai_name}**")

    # ── モード切り替えタブ ──────────────────────────────────────────
    tab_edit, tab_builder = st.tabs(["📝 直接編集モード", "🧩 セクション別調整モード"])

    # ── 直接編集モード ──────────────────────────────────────────────
    with tab_edit:
        draft_val = st.session_state.sg_edited_draft or st.session_state.sg_draft
        edited = st.text_area(
            "台本（直接編集できます）",
            value=draft_val,
            height=520,
            key="sg_direct_edit",
        )
        char_count = len(edited)
        if char_count < target_min:
            st.warning(f"📏 **{char_count}文字** ／ 目標 {target_min}〜{target_max}文字（あと {target_min - char_count}文字必要）")
        elif char_count > target_max:
            st.warning(f"📏 **{char_count}文字** ／ 目標 {target_min}〜{target_max}文字（{char_count - target_max}文字オーバー）")
        else:
            st.success(f"📏 **{char_count}文字** ／ 目標範囲内 ✅")

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
                with st.spinner(f"🔄 台本を再生成中... ({char_range})"):
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
            if st.button("ファクトチェック → 完成 →", type="primary", key="tab1_next"):
                st.session_state.sg_edited_draft = edited
                st.session_state.sg_fc_results = []
                st.session_state.sg_step = 4
                st.rerun()

    # ── セクション別調整モード ──────────────────────────────────────
    with tab_builder:
        st.caption("台本をセクションに分割し、各部分ごとに5つの候補から選んで台本を組み立てます")

        sections = st.session_state.sg_sections

        # セクション未生成なら生成ボタン
        if not sections:
            draft_for_split = st.session_state.sg_edited_draft or st.session_state.sg_draft
            if st.button("🧩 セクション別候補を生成する（AI分割＋各5候補）", type="primary", key="gen_sections"):
                with st.spinner("AIが台本をセクションに分割してバリアントを生成中... （少し時間がかかります）"):
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
                            # セクションテキストのデフォルト値をセッションに設定
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
                # ラジオ変更時: selected_idx を更新してテキストエリアもリセット
                if chosen != prev_sel:
                    st.session_state.sg_sections[i]["selected_idx"] = chosen
                    st.session_state[f"sg_sec_text_{i}"] = sec["variants"][chosen]
                    st.rerun()

                # 選択した候補のテキストを編集可能テキストエリアで表示
                text_key = f"sg_sec_text_{i}"
                if text_key not in st.session_state:
                    st.session_state[text_key] = (
                        sec["variants"][prev_sel] if sec["variants"] else sec["original"]
                    )
                st.text_area(
                    "✏️ 微調整（直接編集可）",
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
            st.markdown("#### 📄 組み上がった台本プレビュー")
            if char_assembled < target_min:
                st.warning(f"📏 **{char_assembled}文字** ／ 目標 {target_min}〜{target_max}文字（あと {target_min - char_assembled}文字）")
            elif char_assembled > target_max:
                st.warning(f"📏 **{char_assembled}文字** ／ 目標 {target_min}〜{target_max}文字（{char_assembled - target_max}文字オーバー）")
            else:
                st.success(f"📏 **{char_assembled}文字** ／ 目標範囲内 ✅")
            st.text_area("完成台本", value=assembled, height=300, disabled=True, key="sg_assembled_preview")

            col_reset, col_next = st.columns([1, 2])
            with col_reset:
                if st.button("🔄 セクションをリセット", key="reset_sections"):
                    st.session_state.sg_sections = []
                    for i in range(10):
                        st.session_state.pop(f"sg_sec_text_{i}", None)
                    st.rerun()
            with col_next:
                if st.button("この構成で確定 → ファクトチェックへ", type="primary", key="confirm_sections"):
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

        # 台本プレビュー（小さく）
        char_preview = len(draft)
        st.markdown(
            f'<div style="background:#F8FAFF;border:1px solid #C7D2FE;border-radius:10px;'
            f'padding:14px 16px;margin-bottom:16px;">'
            f'<span style="font-size:0.8rem;color:#6B7280;">確認する台本 — {char_preview}文字</span></div>',
            unsafe_allow_html=True,
        )
        with st.expander("台本の内容を確認する"):
            st.text(draft)

        st.markdown("""
<div style="background:linear-gradient(135deg,#EEF2FF,#F5F3FF);border-radius:12px;
padding:20px 24px;margin:12px 0 20px;">
<h4 style="margin:0 0 8px;color:#3730A3;">🔍 4 AI 並列ファクトチェック</h4>
<p style="margin:0;color:#4B5563;font-size:0.9rem;">
Claude Sonnet・ChatGPT (GPT-4o)・Gemini 2.0 Flash・Grok 3 Mini が同時並列で<br>
台本の事実的主張を独立検証します。完了まで約2〜3分かかります。
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
                    fc_s = "⚙️ 検証中" if t_fc.is_alive() else "✅ 完了"
                    ti_s = "⚙️ 生成中" if t_ti.is_alive() else "✅ 完了"
                    status_ph.info(f"ファクトチェック: **{fc_s}** ｜ タイトル生成: **{ti_s}**")
                    dot = "●" * (elapsed % 4)
                    ai_status.caption(f"🤖 並列実行中: {' / '.join(MODEL_LABELS)} {dot}")
                    time.sleep(1)
                t_fc.join(); t_ti.join()
                prog.progress(100)
                status_ph.empty(); ai_status.empty()

                if "fc_error" in result_holder:
                    st.error(f"ファクトチェックエラー: {result_holder['fc_error']}")
                else:
                    st.session_state.sg_fc_results = result_holder.get("fc", [])
                    st.session_state.sg_titles = result_holder.get("titles", "")
                    # 最終セクションビルダー用リセット
                    st.session_state["sg_final_sections"] = []
                    st.rerun()

    # ────────────────────────────────────────────────────────────────
    # B) ファクトチェック完了 → 結果表示 + 最終調整 + 評価
    # ────────────────────────────────────────────────────────────────
    else:
        _, ai_name = st.session_state.sg_current_ai
        titles = st.session_state.sg_titles
        fc_results = st.session_state.sg_fc_results

        # やり直しボタン（右上に小さく配置）
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
            # タイトルと サムネイルを分けて表示
            import re as _re
            title_lines = [l for l in titles.split("\n")
                           if _re.match(r"^\d+\.", l.strip())]
            thumb_lines  = [l for l in titles.split("\n")
                            if _re.match(r"^\d+\.", l.strip()) and l in titles.split("## サムネイル")[1]
                            ] if "## サムネイル" in titles else []

            col_t, col_s = st.columns([3, 2])
            with col_t:
                st.markdown(
                    '<div style="background:#FAFAFA;border:1px solid #E5E7EB;border-radius:10px;'
                    'padding:16px 18px;">'
                    '<div style="font-size:0.8rem;color:#6B7280;margin-bottom:10px;font-weight:600;">'
                    '📋 タイトル候補</div>',
                    unsafe_allow_html=True,
                )
                # タイトル番号付きリスト部分を綺麗に表示
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
                    '<div style="background:#FAFAFA;border:1px solid #E5E7EB;border-radius:10px;'
                    'padding:16px 18px;">'
                    '<div style="font-size:0.8rem;color:#6B7280;margin-bottom:10px;font-weight:600;">'
                    '🖼️ サムネイル案</div>',
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
                            f'<div style="background:#EEF2FF;border-radius:6px;padding:8px 10px;'
                            f'margin-bottom:6px;font-size:0.88rem;">{line}</div>',
                            unsafe_allow_html=True,
                        )
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")

        # ─ ファクトチェック 4カラム ───────────────────────────────────
        st.markdown("### 🔬 ファクトチェック結果（4 AI 並列）")

        MODEL_STYLES = {
            "Claude Sonnet 4.6":  {"color": "#7C3AED", "bg": "#F5F3FF", "icon": "🟣"},
            "ChatGPT (GPT-4o)":   {"color": "#059669", "bg": "#ECFDF5", "icon": "🟢"},
            "Gemini 2.0 Flash":   {"color": "#1D4ED8", "bg": "#EFF6FF", "icon": "🔵"},
            "Grok 3 Mini":        {"color": "#374151", "bg": "#F9FAFB", "icon": "⚫"},
        }
        VERDICT_MAP = {
            "✅": ("概ね正確", "#059669", "#ECFDF5"),
            "⚠️": ("一部要注意", "#D97706", "#FFFBEB"),
            "❌": ("問題あり",   "#DC2626", "#FEF2F2"),
            "❓": ("確認中",     "#6B7280", "#F9FAFB"),
        }

        # サマリーバー（4モデルの判定を横一列）
        smry_cols = st.columns(4)
        for col_s2, res in zip(smry_cols, fc_results):
            if res is None:
                continue
            mname = res.get("model_name", "")
            style = MODEL_STYLES.get(mname, {"color": "#4F46E5", "bg": "#EEF2FF", "icon": "🤖"})
            verdict = res.get("verdict", "❓")
            v_label, v_color, v_bg = VERDICT_MAP.get(verdict, ("確認中", "#6B7280", "#F9FAFB"))
            with col_s2:
                st.markdown(
                    f'<div style="text-align:center;padding:12px 8px;'
                    f'background:{style["bg"]};border-radius:10px;'
                    f'border:2px solid {style["color"]}30;">'
                    f'<div style="font-size:0.78rem;font-weight:700;color:{style["color"]};'
                    f'margin-bottom:6px;">{style["icon"]} {mname}</div>'
                    f'<div style="font-size:1.6rem;">{verdict}</div>'
                    f'<div style="font-size:0.75rem;color:{v_color};font-weight:600;'
                    f'background:{v_bg};border-radius:4px;padding:2px 6px;margin-top:4px;'
                    f'display:inline-block;">{v_label}</div>'
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
                                st.markdown(f"---\n**🔹 {stripped[4:]}**")
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
                st.warning(f"📏 **{char_count}文字** ／ 目標 {target_min}〜{target_max}文字")
            elif char_count > target_max:
                st.warning(f"📏 **{char_count}文字** ／ 目標オーバー")
            else:
                st.success(f"📏 **{char_count}文字** ／ 目標範囲内 ✅")

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
            st.caption("ファクトチェックの指摘を踏まえ、セクションごとに5候補から内容を選んで最終台本を組み立てます")

            # sg_final_sections が初期化されているか確認
            if "sg_final_sections" not in st.session_state:
                st.session_state["sg_final_sections"] = []

            final_sections = st.session_state["sg_final_sections"]
            base_script = st.session_state.sg_edited_draft

            if not final_sections:
                # FC結果のサマリーを文脈として渡す
                fc_summary = "\n".join(
                    f"[{r.get('model_name','')}の指摘] "
                    + (r.get("text","")[:400] if r.get("text") else r.get("error",""))
                    for r in fc_results if r
                )[:1200]

                if st.button("🧩 セクション別候補を生成する（ファクトチェック結果を反映）",
                             type="primary", key="gen_final_sections"):
                    with st.spinner("AIがセクションを分割して各5候補を生成中..."):
                        try:
                            import concurrent.futures
                            from script_crew import split_script_sections, generate_section_variants

                            raw_secs = split_script_sections(base_script, script_type, model_id)

                            def gen_final(i, sec):
                                ctx = "\n\n".join(
                                    raw_secs[j]["content"] for j in range(i)
                                )
                                # ファクトチェック指摘を文脈に追加
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
                    # ラジオボタンで全5候補を一覧表示
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
                        "✏️ 微調整（直接編集可）",
                        key=text_key_f,
                        height=90,
                    )

                assembled_final = "\n\n".join(
                    st.session_state.get(f"sg_final_sec_text_{i}", s["original"])
                    for i, s in enumerate(final_sections)
                )
                char_assembled = len(assembled_final)

                st.markdown("---")
                st.markdown("#### 📄 組み上がった最終台本")
                if char_assembled < target_min:
                    st.warning(f"📏 **{char_assembled}文字** ／ 目標 {target_min}〜{target_max}文字（あと {target_min - char_assembled}文字）")
                elif char_assembled > target_max:
                    st.warning(f"📏 **{char_assembled}文字** ／ {char_assembled - target_max}文字オーバー")
                else:
                    st.success(f"📏 **{char_assembled}文字** ／ 目標範囲内 ✅")
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
                    if st.button("✅ この台本で確定する", type="primary", key="fix_final_script"):
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
<div style="background:linear-gradient(135deg,#F0FDF4,#ECFDF5);border-radius:12px;
padding:20px 24px;border:1px solid #A7F3D0;">
<h4 style="margin:0 0 6px;color:#065F46;">⭐ この台本を評価してください</h4>
<p style="margin:0;color:#047857;font-size:0.88rem;">評価結果をAIが分析し、次回の生成に自動反映されます</p>
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
                with st.spinner("🔍 台本の好評ポイントをAIが分析中..."):
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
<div style="background:#ECFDF5;border:1px solid #6EE7B7;border-radius:10px;padding:16px 18px;">
<h4 style="color:#065F46;margin:0 0 6px;">✅ 好評として保存しました！</h4>
<p style="color:#047857;margin:0;font-size:0.88rem;">次回の台本生成に自動反映されます</p>
</div>
""", unsafe_allow_html=True)
                elements = st.session_state.sg_learned_elements
                if elements and elements != ["（分析データなし）"]:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("**📚 今回学習した好評ポイント**")
                    for el in elements:
                        st.markdown(
                            f'<div style="background:#F0FDF4;border-left:3px solid #059669;'
                            f'padding:8px 12px;border-radius:4px;margin:4px 0;font-size:0.88rem;">'
                            f'✓ {el}</div>',
                            unsafe_allow_html=True,
                        )

        elif rating_mode == "bad":
            if not st.session_state.sg_saved:
                st.markdown("""
<div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:10px;padding:16px 18px;margin-bottom:16px;">
<h4 style="color:#991B1B;margin:0 0 4px;">💬 改善フィードバック</h4>
<p style="color:#B91C1C;margin:0;font-size:0.88rem;">何が問題だったか教えてください。次回の生成に反映されます</p>
</div>
""", unsafe_allow_html=True)
                ng_themes = st.multiselect(
                    "🚫 NGにするテーマ", options=st.session_state.sg_selected_themes,
                    default=[], key="sg_bad_ng_themes",
                )
                ng_ideas = st.multiselect(
                    "🚫 NGにするアイデア", options=st.session_state.sg_selected_ideas or [],
                    default=[], key="sg_bad_ng_ideas",
                )
                bad_note = st.text_input(
                    "💬 悪かった点を一言で（任意）",
                    placeholder="例：感情訴求が弱かった、情報が古かった など",
                    key="sg_bad_note",
                )
                if st.button("💾 フィードバックを保存して学習させる", type="primary"):
                    with st.spinner("🔍 AIが改善パターンを分析中..."):
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
                st.warning("⚠️ 改善フィードバックを保存しました。次回の生成に反映されます")
                if st.session_state.sg_learned_pattern:
                    st.info(f"**📚 学習した改善パターン：** {st.session_state.sg_learned_pattern}")

        st.markdown("---")
        if st.button("🔄 新しい台本を生成する", type="secondary"):
            reset_all()
            st.rerun()


# ─── フッター ─────────────────────────────────────────────────────────
if step > 0:
    st.divider()
    if st.button("↩️ 最初からやり直す", type="secondary"):
        reset_all()
        st.rerun()
