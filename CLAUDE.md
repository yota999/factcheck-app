# 台本生成システム

## このプロジェクトについて
- Streamlit製のWebアプリ（YouTube・リール動画の台本生成）
- GitHub: yota999/factcheck-app（masterブランチ）
- 本番URL: factcheck-app-appppdkmaxjagghw9gtgak6p.streamlit.app
- Streamlit Cloudに自動デプロイ（push後1〜2分で反映）

## ファイル構成
- `script_crew.py` — 台本生成のAIエージェント処理（メインロジック）
- `memory_manager.py` — 学習データ・履歴管理（Supabase）
- `pages/1_台本生成.py` — 台本生成UI（Streamlit）
- `pages/2_生成履歴.py` — 生成履歴UI
- `app.py` — トップページ（ナビゲーション）

## 技術スタック
- Python / Streamlit（wide layout）
- LiteLLM（4AI並列呼び出し）
- Supabase PostgreSQL（学習データ・履歴のクラウドDB）
- ThreadPoolExecutor（4本並列生成）

## 台本生成の仕組み
### 生成フロー
1. Step 0: YouTube台本 or リール台本を選択 → 即Step 1へ
2. Step 1: 素材テキストを入力（ブログ・メモ・箇条書きなど何でもOK）
3. Step 2: 4つのAIが並列で台本を生成 → タブで読み比べて1本を選択
4. Step 3: 選択した台本を部分修正・ブラッシュアップ → 完成

### 使用モデル（4本並列）
- Claude Sonnet 4.6（anthropic）
- GPT-4o 2024-11-20（openai）
- Gemini 2.5 Flash（google）
- Grok 3（xai）

### ペルソナ設定
- コーチ名：町田耀大
- 実績：トレーナー歴15年・6500人以上指導
- ターゲット：35歳以上（主に40〜50代）の女性
- 一人称：僕 / 二人称：あなた・女性

### CTA（固定・自動追加）
- YouTube：`YOUTUBE_CTA`（締め文＋LINE誘導＋チャンネル登録）
- リール：`REEL_CTA_FOOTER`（固定）＋ `_generate_reel_cta_intro()`（台本内容に合わせて動的生成）
- AIはCTAを生成しない。生成後に自動でくっつける

### 学習システム
- 台本を修正するたびに改善ルールを自動抽出・保存（最大20件）
- `memory/history.json`（ローカル保存・gitignore）
- `get_edit_improvements()` で次回生成時に反映

## 主要な定数（script_crew.py）
- `YOUTUBE_PERSONA` — YouTubeペルソナ＋入力形式
- `YOUTUBE_STRUCTURE` — YouTube台本の7セクション構造ルール
- `YOUTUBE_CTA` — YouTube用固定CTA全文
- `REEL_PERSONA` — リールペルソナ＋入力形式
- `REEL_STRUCTURE` — リール台本の6セクション構造ルール
- `REEL_CTA_FOOTER` — リール用固定CTA末尾

## 文字数目標
- YouTube台本：5000文字以上（CTAは別途自動追加）
- リール台本：850〜950文字（CTAは別途自動追加）
- 不足時は自動展開パス（4700文字未満で2回目の生成をかける）

## デプロイ手順
```
git add <ファイル>
git commit -m "説明"
git push origin master
```

## 作業ルール
- コードを変更する前に「何をするか」を一言確認する
- 小さく確実に進める
- .envファイルは絶対に読まない・表示しない
- APIキーはチャットに表示しない
- memory/history.json はgitignore済み（ローカル学習データ）
