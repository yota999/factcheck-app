import os
import time
import threading
import datetime

import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=True)

try:
    for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY",
                "XAI_API_KEY", "SERPER_API_KEY"]:
        if key in st.secrets and not os.getenv(key):
            os.environ[key] = st.secrets[key]
except Exception:
    pass

st.set_page_config(
    page_title="マルチAI ファクトチェック",
    page_icon="🔍",
    layout="wide",
)

# ─── CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans JP', sans-serif; }

.page-header {
    background: linear-gradient(135deg, #0F172A 0%, #1E3A5F 40%, #1D4ED8 100%);
    border-radius: 18px; padding: 28px 32px 24px;
    color: white; margin-bottom: 24px;
    box-shadow: 0 8px 32px rgba(29,78,216,.25);
}
.page-header h1 { margin:0; font-size:1.8rem; font-weight:800; letter-spacing:-.02em; }
.page-header p  { margin:8px 0 0; opacity:.75; font-size:.88rem; line-height:1.6; }

.model-badge {
    display:inline-flex; align-items:center; gap:6px;
    padding:5px 12px; border-radius:20px; font-size:.8rem;
    font-weight:600; margin:3px;
}
.fc-summary-card {
    border-radius:12px; padding:16px 18px; border:1.5px solid;
    text-align:center; margin-bottom:8px;
}
.verdict-chip {
    display:inline-block; padding:4px 12px; border-radius:20px;
    font-size:.78rem; font-weight:700; margin-top:6px;
}
.diff-original {
    background:#FEF2F2; border-left:3px solid #EF4444;
    border-radius:0 8px 8px 0; padding:10px 14px;
    margin:6px 0; font-size:.88rem; line-height:1.7;
    white-space:pre-wrap; word-break:break-all;
}
.diff-corrected {
    background:#F0FDF4; border-left:3px solid #22C55E;
    border-radius:0 8px 8px 0; padding:10px 14px;
    margin:6px 0; font-size:.88rem; line-height:1.7;
    white-space:pre-wrap; word-break:break-all;
}
.change-item {
    background:#EFF6FF; border-left:3px solid #3B82F6;
    border-radius:0 8px 8px 0; padding:8px 12px;
    margin:4px 0; font-size:.85rem; line-height:1.6;
}
</style>
""", unsafe_allow_html=True)

# ─── ヘッダー ──────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
  <h1>🔍 マルチAI ファクトチェック</h1>
  <p>Claude × ChatGPT × Gemini × Grok が独立並列で事実検証 → 自動修正まで一気に実行</p>
</div>
""", unsafe_allow_html=True)

# ─── Session State ─────────────────────────────────────────────────────
_DEFAULTS = {
    "fc_input": "",
    "fc_results": [],
    "fc_correction": {},
    "fc_revision": {},
    "fc_running": False,
    "fc_done": False,
    "fc_variants": [],
}
for k, v in _DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─── 入力エリア ────────────────────────────────────────────────────────
st.markdown("### 📝 検証する文章を入力")

col_input, col_guide = st.columns([3, 1])
with col_input:
    tab_paste, tab_file = st.tabs(["テキストを貼り付け", "ファイルを読み込む"])

    with tab_paste:
        user_text = st.text_area(
            "文章を貼り付け",
            height=220,
            placeholder="ファクトチェックしたい台本・文章をここに貼り付けてください（目安：1000文字以内）",
            label_visibility="collapsed",
            key="fc_text_area",
        )

    with tab_file:
        uploaded = st.file_uploader("テキストファイル（.txt）", type=["txt"])
        if uploaded:
            user_text = uploaded.read().decode("utf-8")
            st.success(f"読み込み完了: {len(user_text)}文字")

with col_guide:
    st.markdown("""
<div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:12px;padding:16px 18px;margin-top:32px;">
<div style="font-weight:700;color:#1D4ED8;margin-bottom:10px;">📋 使い方</div>
<div style="font-size:.83rem;color:#374151;line-height:1.8;">
①&nbsp;文章を貼り付ける<br>
②&nbsp;ファクトチェック開始<br>
③&nbsp;4つのAIが並列検証<br>
④&nbsp;自動修正を生成<br>
⑤&nbsp;修正版をコピー
</div>
</div>
""", unsafe_allow_html=True)

# 文字数表示
input_text = user_text if "user_text" in dir() and user_text else st.session_state.fc_input
if input_text:
    char_count = len(input_text)
    color = "#DC2626" if char_count > 1500 else "#D97706" if char_count > 1000 else "#059669"
    st.markdown(
        f'<div style="font-size:.84rem;color:{color};font-weight:600;margin-top:4px;">'
        f'文字数: {char_count}文字'
        f'{"　⚠️ 1000文字超えています" if char_count > 1000 else ""}'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ─── 実行ボタン ────────────────────────────────────────────────────────
col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    run_btn = st.button(
        "🚀 ファクトチェック開始",
        type="primary",
        use_container_width=True,
        disabled=not bool(input_text and input_text.strip()),
    )

# ─── FC実行 ────────────────────────────────────────────────────────────
if run_btn and input_text and input_text.strip():
    st.session_state.fc_input = input_text
    st.session_state.fc_results = []
    st.session_state.fc_correction = {}
    st.session_state.fc_done = False
    st.session_state.fc_variants = []

    result_holder = {}

    def _run_fc():
        try:
            from script_crew import factcheck_parallel, auto_correct_script
            fc_results = factcheck_parallel(input_text)
            result_holder["fc"] = fc_results
            result_holder["fc_done"] = True  # FCフェーズ完了

            # 問題があれば自動修正も続けて実行
            verdicts = [r.get("verdict", "❓") for r in fc_results if r]
            if any(v in ["⚠️", "❌"] for v in verdicts):
                correction = auto_correct_script(
                    original=input_text,
                    fc_results=fc_results,
                    model="anthropic/claude-sonnet-4-6",
                )
                result_holder["correction"] = correction
        except Exception as e:
            result_holder["error"] = str(e)

    t = threading.Thread(target=_run_fc, daemon=True)
    t.start()

    # 進捗表示
    st.markdown("---")
    st.markdown("### ⚙️ ファクトチェック＋自動修正を実行中...")

    MODEL_LABELS = [
        ("Claude Sonnet 4.6", "🟣"),
        ("ChatGPT (GPT-4o)", "🟢"),
        ("Gemini 2.5 Flash", "🔵"),
        ("Grok 3 Mini", "⚫"),
    ]
    prog = st.progress(0)
    status_ph = st.empty()
    ai_cols = st.columns(4)
    ai_placeholders = []
    for i, (mname, icon) in enumerate(MODEL_LABELS):
        with ai_cols[i]:
            p = st.empty()
            p.markdown(
                f'<div style="text-align:center;padding:12px;background:#F3F4F6;'
                f'border-radius:10px;border:1.5px solid #E5E7EB;">'
                f'<div style="font-size:1.2rem;">{icon}</div>'
                f'<div style="font-size:.78rem;font-weight:600;color:#6B7280;margin-top:4px;">{mname}</div>'
                f'<div style="font-size:.72rem;color:#9CA3AF;margin-top:2px;">検証中...</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            ai_placeholders.append(p)

    elapsed = 0
    while t.is_alive():
        elapsed += 1
        prog.progress(min(90, elapsed * 2))
        dots = "." * ((elapsed % 3) + 1)
        if result_holder.get("fc_done"):
            status_ph.info(f"✅ ファクトチェック完了 → 自動修正を生成中{dots}")
        else:
            status_ph.info(f"4つのAIが独立並列でファクトチェック中{dots}")
        time.sleep(1)

    t.join()
    prog.progress(100)
    status_ph.empty()

    # 完了マーク
    for i, (mname, icon) in enumerate(MODEL_LABELS):
        ai_placeholders[i].markdown(
            f'<div style="text-align:center;padding:12px;background:#F0FDF4;'
            f'border-radius:10px;border:1.5px solid #A7F3D0;">'
            f'<div style="font-size:1.2rem;">{icon}</div>'
            f'<div style="font-size:.78rem;font-weight:600;color:#059669;margin-top:4px;">{mname}</div>'
            f'<div style="font-size:.72rem;color:#059669;margin-top:2px;">✅ 完了</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if "error" in result_holder:
        st.error(f"エラー: {result_holder['error']}")
    else:
        st.session_state.fc_results = result_holder.get("fc", [])
        if "correction" in result_holder:
            st.session_state.fc_correction = result_holder["correction"]
        st.session_state.fc_done = True
        st.rerun()


# ─── 結果表示 ──────────────────────────────────────────────────────────
if st.session_state.fc_done and st.session_state.fc_results:
    fc_results = st.session_state.fc_results

    MODEL_STYLES = {
        "Claude Sonnet 4.6": {"color": "#7C3AED", "bg": "#F5F3FF", "border": "#DDD6FE", "icon": "🟣"},
        "ChatGPT (GPT-4o)":  {"color": "#059669", "bg": "#ECFDF5", "border": "#A7F3D0", "icon": "🟢"},
        "Gemini 2.5 Flash":  {"color": "#1D4ED8", "bg": "#EFF6FF", "border": "#BFDBFE", "icon": "🔵"},
        "Grok 3 Mini":       {"color": "#374151", "bg": "#F9FAFB", "border": "#D1D5DB", "icon": "⚫"},
    }
    VERDICT_MAP = {
        "✅": ("概ね正確",   "#059669", "#ECFDF5"),
        "⚠️": ("一部要注意", "#D97706", "#FFFBEB"),
        "❌": ("問題あり",   "#DC2626", "#FEF2F2"),
        "❓": ("確認中",     "#6B7280", "#F9FAFB"),
    }

    st.markdown("---")
    st.markdown("### 🔬 ファクトチェック結果")

    # サマリーバッジ
    sum_cols = st.columns(4)
    for col, res in zip(sum_cols, fc_results):
        if not res:
            continue
        mname = res.get("model_name", "")
        style = MODEL_STYLES.get(mname, {"color":"#4F46E5","bg":"#EEF2FF","border":"#C7D2FE","icon":"🤖"})
        verdict = res.get("verdict", "❓")
        v_label, v_color, v_bg = VERDICT_MAP.get(verdict, ("確認中","#6B7280","#F9FAFB"))
        with col:
            st.markdown(
                f'<div class="fc-summary-card" style="background:{style["bg"]};border-color:{style["border"]};">'
                f'<div style="font-size:1.4rem;">{style["icon"]}</div>'
                f'<div style="font-weight:700;font-size:.88rem;color:{style["color"]};margin-top:4px;">{mname}</div>'
                f'<div style="font-size:1.8rem;margin:4px 0;">{verdict}</div>'
                f'<div class="verdict-chip" style="color:{v_color};background:{v_bg};">{v_label}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # 詳細タブ
    tab_labels = [
        f'{MODEL_STYLES.get(r.get("model_name",""),{}).get("icon","🤖")} {r.get("model_name","")}'
        for r in fc_results if r
    ]
    if tab_labels:
        tabs = st.tabs(tab_labels)
        for tab, res in zip(tabs, [r for r in fc_results if r]):
            with tab:
                if res.get("error"):
                    st.error(f"APIエラー: {res['error']}")
                elif res.get("text"):
                    for line in res["text"].split("\n"):
                        s = line.strip()
                        if not s:
                            st.markdown("")
                        elif s.startswith("## "):
                            st.markdown(f"**{s[3:]}**")
                        elif s.startswith("### "):
                            st.markdown(f"---\n**{s[4:]}**")
                        elif "✅" in s:
                            st.success(s)
                        elif "❌" in s:
                            st.error(s)
                        elif "⚠️" in s:
                            st.warning(s)
                        else:
                            st.write(s)

    st.markdown("---")

    # ─── 自動修正 ────────────────────────────────────────────────────
    st.markdown("### ✏️ 自動修正")
    st.caption("4つのAIの指摘を統合して、問題のある表現・数字を自動修正した台本を生成します")

    # 問題があるか確認
    verdicts = [r.get("verdict","❓") for r in fc_results if r]
    has_issues = any(v in ["⚠️","❌"] for v in verdicts)

    if not has_issues:
        st.success("✅ 4つのAI全てで概ね正確と判定されました。修正は不要です。")
    else:
        # 修正済みなら表示、未実行なら生成ボタン
        if not st.session_state.fc_correction:
            col_fix_l, col_fix_c, col_fix_r = st.columns([1, 2, 1])
            with col_fix_c:
                if st.button("🔧 自動修正版を生成する", type="primary", use_container_width=True):
                    with st.spinner("AIが問題箇所を修正中..."):
                        try:
                            from script_crew import auto_correct_script
                            correction = auto_correct_script(
                                original=st.session_state.fc_input,
                                fc_results=fc_results,
                                model="anthropic/claude-sonnet-4-6",
                            )
                            st.session_state.fc_correction = correction
                        except Exception as e:
                            st.error(f"修正エラー: {e}")
                    st.rerun()

        if st.session_state.fc_correction:
            correction = st.session_state.fc_correction

            if correction.get("error"):
                st.error(f"修正エラー: {correction['error']}")
            else:
                col_orig, col_corr = st.columns(2)

                with col_orig:
                    st.markdown("**修正前**")
                    st.markdown(
                        f'<div class="diff-original">{st.session_state.fc_input}</div>',
                        unsafe_allow_html=True,
                    )

                with col_corr:
                    st.markdown("**修正後**")
                    corrected_text = correction.get("corrected", "")
                    st.markdown(
                        f'<div class="diff-corrected">{corrected_text}</div>',
                        unsafe_allow_html=True,
                    )
                    st.text_area(
                        "修正版（コピー用）",
                        value=corrected_text,
                        height=200,
                        key="fc_copy_area",
                    )

                # 修正箇所の説明
                changes = correction.get("changes", "")
                if changes:
                    st.markdown("#### 📋 修正箇所の説明")
                    for line in changes.split("\n"):
                        s = line.strip("- •・").strip()
                        if s:
                            st.markdown(
                                f'<div class="change-item">・{s}</div>',
                                unsafe_allow_html=True,
                            )

                st.markdown("<br>", unsafe_allow_html=True)

                # 再修正ボタン
                col_redo, col_new = st.columns(2)
                with col_redo:
                    if st.button("🔄 修正をやり直す", use_container_width=True):
                        st.session_state.fc_correction = {}
                        st.session_state.fc_revision = {}
                        st.rerun()
                with col_new:
                    if st.button("📝 新しいテキストをチェック", use_container_width=True):
                        for k in ["fc_input","fc_results","fc_correction","fc_done","fc_revision"]:
                            st.session_state[k] = _DEFAULTS[k]
                        st.rerun()

                # ── 追加修正指示セクション ────────────────────────────
                st.markdown("---")
                st.markdown("#### ✍️ 修正版にさらに指示を出す")
                st.caption("修正版テキストを元に、追加の指示で文章を改訂できます。複数回繰り返すことも可能です。")

                instruction_input = st.text_area(
                    "修正の指示",
                    height=100,
                    placeholder="例：「第2段落の表現をもっと柔らかくしてください」「数字の部分を削除して」など",
                    key="fc_revision_instruction",
                )

                # 改訂のベースは「前の改訂版」or「自動修正版」
                base_text_for_revision = (
                    st.session_state.fc_revision.get("revised") or corrected_text
                )

                col_ins_l, col_ins_c, col_ins_r = st.columns([1, 2, 1])
                with col_ins_c:
                    if st.button(
                        "✏️ 指示を反映して改訂",
                        use_container_width=True,
                        disabled=not bool(instruction_input and instruction_input.strip()),
                        key="apply_revision_btn",
                    ):
                        with st.spinner("指示を反映して改訂中..."):
                            try:
                                from script_crew import revise_with_instruction
                                revision = revise_with_instruction(
                                    current_text=base_text_for_revision,
                                    instruction=instruction_input,
                                    original=st.session_state.fc_input,
                                )
                                st.session_state.fc_revision = revision
                            except Exception as e:
                                st.error(f"改訂エラー: {e}")
                        st.rerun()

                if st.session_state.fc_revision:
                    revision = st.session_state.fc_revision
                    if revision.get("error"):
                        st.error(f"改訂エラー: {revision['error']}")
                    else:
                        revised_text = revision.get("revised", "")
                        st.markdown("**改訂後**")
                        st.markdown(
                            f'<div class="diff-corrected">{revised_text}</div>',
                            unsafe_allow_html=True,
                        )
                        st.text_area(
                            "改訂版（コピー用）",
                            value=revised_text,
                            height=200,
                            key="fc_revision_copy_area",
                        )
                        revision_changes = revision.get("changes", "")
                        if revision_changes:
                            st.markdown("**変更箇所**")
                            for line in revision_changes.split("\n"):
                                s = line.strip("- •・").strip()
                                if s:
                                    st.markdown(
                                        f'<div class="change-item">・{s}</div>',
                                        unsafe_allow_html=True,
                                    )
                        if st.button("🗑️ 改訂をリセット", key="reset_revision"):
                            st.session_state.fc_revision = {}
                            st.rerun()

    # ─── バリアント生成 ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🎨 異なる角度で3バリアントを生成")
    st.caption("ファクトチェック済みの事実・数字を維持しながら、切り口を変えた台本を3つ並列生成します")

    # ベーステキスト（修正版があればそちらを優先）
    base_for_variant = (
        st.session_state.fc_correction.get("corrected", "")
        or st.session_state.fc_input
    )
    if st.session_state.fc_correction.get("corrected"):
        st.info("💡 修正版台本をベースにバリアントを生成します")

    if not st.session_state.fc_variants:
        col_v_l, col_v_c, col_v_r = st.columns([1, 2, 1])
        with col_v_c:
            if st.button("✨ 3つのバリアントを生成する", type="primary", use_container_width=True):
                with st.spinner("3つの角度で台本を並列生成中... （30秒〜1分）"):
                    try:
                        from script_crew import generate_fc_variants
                        variants = generate_fc_variants(
                            base_script=base_for_variant,
                            n=3,
                            model="anthropic/claude-sonnet-4-6",
                        )
                        st.session_state.fc_variants = variants
                    except Exception as e:
                        st.error(f"生成エラー: {e}")
                st.rerun()
    else:
        variants = st.session_state.fc_variants
        tab_labels = [f"✏️ {v['angle_name']}" for v in variants]
        tabs = st.tabs(tab_labels)
        for tab, v in zip(tabs, variants):
            with tab:
                if v.get("error"):
                    st.error(f"生成エラー: {v['error']}")
                elif v.get("text"):
                    char_v = len(v["text"])
                    st.caption(f"{char_v}文字")
                    st.text_area(
                        "台本（コピー用）",
                        value=v["text"],
                        height=300,
                        key=f"variant_{v['angle_key']}",
                    )

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 バリアントを再生成する", use_container_width=True):
            st.session_state.fc_variants = []
            st.rerun()

    # ─── 最初からやり直す ─────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("↩️ 最初からやり直す", type="secondary"):
        for k in ["fc_input","fc_results","fc_correction","fc_revision","fc_done","fc_variants"]:
            st.session_state[k] = _DEFAULTS[k]
        st.rerun()

# ─── フッター ──────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    '<div style="text-align:center;color:#9CA3AF;font-size:.78rem;">'
    'マルチAI ファクトチェックシステム — Claude × ChatGPT × Gemini × Grok 並列検証'
    '</div>',
    unsafe_allow_html=True,
)
