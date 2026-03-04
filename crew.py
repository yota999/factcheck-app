import os
from crewai import Agent, Task, Crew, Process, LLM
from dotenv import load_dotenv

load_dotenv(override=True)

# Streamlit Community Cloud の Secrets にも対応
try:
    import streamlit as st
    for key in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "SERPER_API_KEY", "GOOGLE_API_KEY", "XAI_API_KEY"]:
        if key in st.secrets and not os.getenv(key):
            os.environ[key] = st.secrets[key]
except Exception:
    pass


def _build_search_tool():
    serper_key = os.getenv("SERPER_API_KEY")
    if serper_key and serper_key != "your_serper_api_key_here":
        from crewai_tools import SerperDevTool
        return SerperDevTool(n_results=5)
    else:
        from langchain_community.tools import DuckDuckGoSearchRun
        from crewai.tools import BaseTool

        _ddg = DuckDuckGoSearchRun()

        class DuckDuckGoTool(BaseTool):
            name: str = "web_search"
            description: str = "インターネットでキーワード検索を行うツール。医学情報・ニュース・統計を検索できる。"

            def _run(self, query: str) -> str:
                return _ddg.run(query)

        return DuckDuckGoTool()


class FactCheckCrew:
    def __init__(self):
        self._setup_llms()
        self.search_tool = _build_search_tool()

    def _setup_llms(self):
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        google_key = os.getenv("GOOGLE_API_KEY")
        xai_key = os.getenv("XAI_API_KEY")

        # 主力：Claude Sonnet（高品質）
        self.llm_claude = LLM(
            model="anthropic/claude-sonnet-4-6",
            api_key=anthropic_key,
            temperature=0.3,
        )

        # 安価・高速（単純な抽出作業用）
        self.llm_haiku = LLM(
            model="anthropic/claude-haiku-4-5",
            api_key=anthropic_key,
            temperature=0.1,
        )

        # ファクトチェック1：GPT-4o（Claudeと異なる視点）
        self.llm_gpt4o = LLM(
            model="gpt-4o",
            api_key=openai_key,
            temperature=0.2,
        )

        # ファクトチェック2：Gemini 2.0 Flash（第3の視点）
        if google_key and google_key != "your_google_api_key_here":
            self.llm_gemini = LLM(
                model="gemini/gemini-2.5-flash",
                api_key=google_key,
                temperature=0.2,
            )
        else:
            self.llm_gemini = None

        # ファクトチェック3：Grok-2（第4の視点）
        if xai_key and xai_key != "your_xai_api_key_here":
            self.llm_grok = LLM(
                model="xai/grok-3-mini",
                api_key=xai_key,
                temperature=0.2,
            )
        else:
            self.llm_grok = None

    def run(self, text: str) -> str:
        # ① 主張抽出エージェント（Haiku：安価で十分）
        extractor = Agent(
            role="主張抽出スペシャリスト",
            goal="文章から検証すべき全ての事実的主張を漏れなく抽出する",
            backstory=(
                "あなたは文章分析の専門家です。"
                "テキストから数値・統計・医学的主張・因果関係の主張など、"
                "事実として検証できる全ての記述を抽出します。"
            ),
            llm=self.llm_haiku,
            verbose=True,
            max_iter=3,
            allow_delegation=False,
        )

        # ② ファクトチェッカー1：GPT-4o
        checker_gpt = Agent(
            role="ファクトチェッカー（GPT-4o）",
            goal="抽出された主張を科学的根拠に基づいて検証する",
            backstory=(
                "あなたはOpenAI製のAIです。Claudeとは独立した学習データを持ち、"
                "客観的な視点で事実を検証します。"
                "根拠のない主張・誇張・古い情報・相関と因果の混同を厳しく指摘します。"
                "検索ツールで必ず一次情報を確認してから判断します。"
            ),
            tools=[self.search_tool],
            llm=self.llm_gpt4o,
            verbose=True,
            max_iter=5,
            allow_delegation=False,
        )

        # ③ ファクトチェッカー2：Gemini（利用可能な場合）
        if self.llm_gemini:
            checker_gemini = Agent(
                role="ファクトチェッカー（Gemini）",
                goal="GPT-4oとは独立した視点で主張を再検証する",
                backstory=(
                    "あなたはGoogle製のAIです。ClaudeともGPTとも異なる学習データを持ちます。"
                    "特に最新の研究情報・医学ガイドライン・統計データの正確性を重点的に確認します。"
                    "他のAIが見落とした誤りを発見することを使命とします。"
                ),
                tools=[self.search_tool],
                llm=self.llm_gemini,
                verbose=True,
                max_iter=5,
                allow_delegation=False,
            )
        else:
            checker_gemini = None

        # ④ ファクトチェッカー3：Grok（利用可能な場合）
        if self.llm_grok:
            checker_grok = Agent(
                role="ファクトチェッカー（Grok）",
                goal="Claude・GPT・Geminiとは独立した視点で主張を検証する",
                backstory=(
                    "あなたはxAI製のAIです。他の3社とは全く異なる学習データを持ちます。"
                    "特にリアルタイム情報へのアクセスを活かし、最新の研究や報道との整合性を確認します。"
                    "他のAIが合意していても、独自の根拠で異議を唱えることを恐れません。"
                ),
                tools=[self.search_tool],
                llm=self.llm_grok,
                verbose=True,
                max_iter=5,
                allow_delegation=False,
            )
        else:
            checker_grok = None

        # ⑤ 統括・レポート作成：Claude Sonnet
        synthesizer = Agent(
            role="ファクトチェック統括編集長",
            goal="複数AIの検証結果を統合し、最終レポートと修正済み文章を出力する",
            backstory=(
                "あなたは複数のファクトチェッカーの意見を統合する編集長です。"
                "各AIの指摘を公正に評価し、最終的な判断を下します。"
                "誤りは明確に指摘し、正しい情報に基づいた修正案を提示します。"
            ),
            llm=self.llm_claude,
            verbose=True,
            max_iter=3,
            allow_delegation=False,
        )

        # タスク定義
        extract_task = Task(
            description=(
                "以下の文章から、事実として検証できる全ての主張を抽出してください。\n\n"
                "【抽出対象】\n"
                "- 数値・統計（「〇〇%」「〇〇kg」等）\n"
                "- 医学・科学的主張（「〇〇は△△に効果がある」等）\n"
                "- 因果関係の主張（「〇〇をすると△△になる」等）\n"
                "- 研究・調査の引用\n"
                "- 一般的な事実として述べられている内容\n\n"
                "【入力文章】\n"
                f"{text}\n\n"
                "番号付きリストで出力してください。"
            ),
            expected_output="検証すべき主張の番号付きリスト",
            agent=extractor,
        )

        check_gpt_task = Task(
            description=(
                "抽出された主張を一つずつ検索で確認し、以下の形式でレポートを作成してください。\n\n"
                "各主張について：\n"
                "- 【判定】✅ 正確 / ⚠️ 要注意 / ❌ 誤り / ❓ 確認不可\n"
                "- 【根拠】確認した情報源と内容\n"
                "- 【修正案】誤りや要注意の場合のみ記載\n\n"
                "検索ツールを積極的に使い、必ず一次情報を確認すること。"
            ),
            expected_output="主張ごとの判定・根拠・修正案レポート（GPT-4o版）",
            agent=checker_gpt,
            context=[extract_task],
        )

        tasks = [extract_task, check_gpt_task]
        agents = [extractor, checker_gpt, synthesizer]
        final_context = [check_gpt_task]

        if checker_gemini:
            check_gemini_task = Task(
                description=(
                    "GPT-4oとは独立した視点で、抽出された主張を検証してください。\n\n"
                    "各主張について：\n"
                    "- 【判定】✅ 正確 / ⚠️ 要注意 / ❌ 誤り / ❓ 確認不可\n"
                    "- 【根拠】確認した情報源と内容\n"
                    "- 【修正案】誤りや要注意の場合のみ記載\n\n"
                    "特に最新の研究・ガイドラインとの整合性を重点的に確認すること。"
                ),
                expected_output="主張ごとの判定・根拠・修正案レポート（Gemini版）",
                agent=checker_gemini,
                context=[extract_task],
            )
            tasks.append(check_gemini_task)
            agents.insert(-1, checker_gemini)
            final_context.append(check_gemini_task)

        if checker_grok:
            check_grok_task = Task(
                description=(
                    "他のAIとは独立した視点で、抽出された主張を検証してください。\n\n"
                    "各主張について：\n"
                    "- 【判定】✅ 正確 / ⚠️ 要注意 / ❌ 誤り / ❓ 確認不可\n"
                    "- 【根拠】確認した情報源と内容\n"
                    "- 【修正案】誤りや要注意の場合のみ記載\n\n"
                    "最新情報を積極的に活用し、他のAIが見落とした点を発見すること。"
                ),
                expected_output="主張ごとの判定・根拠・修正案レポート（Grok版）",
                agent=checker_grok,
                context=[extract_task],
            )
            tasks.append(check_grok_task)
            agents.insert(-1, checker_grok)
            final_context.append(check_grok_task)

        synthesize_task = Task(
            description=(
                "複数AIのファクトチェック結果を統合し、以下の2つを出力してください。\n\n"
                "【出力1】ファクトチェックレポート\n"
                "- 各主張の最終判定（AIの意見が割れた場合はその旨を明記）\n"
                "- 問題のある主張の修正案\n"
                "- 全体の信頼性評価（高・中・低）とその理由\n\n"
                "【出力2】修正済み文章\n"
                "- 元の文章の誤り・問題箇所を修正したバージョン\n"
                "- 修正箇所は【修正】と【/修正】で囲んで明示する\n"
                "- 正確な情報はそのまま維持する\n\n"
                f"【元の文章（参考）】\n{text}"
            ),
            expected_output="ファクトチェックレポート + 修正済み文章",
            agent=synthesizer,
            context=final_context,
        )
        tasks.append(synthesize_task)

        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
            max_rpm=20,
        )

        result = crew.kickoff()
        return str(result)
