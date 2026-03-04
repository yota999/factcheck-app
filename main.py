import os
import sys
import datetime
from dotenv import load_dotenv


def check_env():
    load_dotenv(override=True)
    missing = []
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        val = os.getenv(key)
        if not val or val.startswith("your_"):
            missing.append(key)

    if missing:
        print("\n[エラー] 以下のAPIキーが .env ファイルに設定されていません:")
        for k in missing:
            print(f"  - {k}")
        print("\n.env ファイルを確認してください。")
        sys.exit(1)


def get_text_input() -> str:
    print("\n" + "=" * 60)
    print("  文章ファクトチェックシステム")
    print("  （Claude × GPT-4o × Gemini マルチAI検証）")
    print("=" * 60)

    print("\n【入力方法を選択してください】")
    print("  1. テキストをここに貼り付ける")
    print("  2. テキストファイルのパスを指定する")

    while True:
        choice = input("\n選択 (1 または 2): ").strip()
        if choice == "1":
            print("\n検証したい文章を貼り付けてください。")
            print("（貼り付けが終わったら、新しい行に「END」と入力してEnterを押してください）\n")
            lines = []
            while True:
                line = input()
                if line.strip() == "END":
                    break
                lines.append(line)
            text = "\n".join(lines).strip()
            if text:
                return text
            print("  文章を入力してください。")

        elif choice == "2":
            path = input("\nファイルパスを入力してください（例: C:\\Users\\yurik\\script.txt）: ").strip()
            path = path.strip('"')
            if not os.path.exists(path):
                print(f"  ファイルが見つかりません: {path}")
                continue
            with open(path, "r", encoding="utf-8") as f:
                text = f.read().strip()
            if text:
                print(f"  読み込み完了（{len(text)}文字）")
                return text
            print("  ファイルが空です。")

        else:
            print("  1 または 2 を入力してください。")


def save_result(result: str) -> str:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"factcheck_{timestamp}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"実行日時: {datetime.datetime.now().strftime('%Y年%m月%d日 %H:%M')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(result)

    return filename


def main():
    check_env()

    text = get_text_input()

    print(f"\n{'=' * 60}")
    print(f"  ファクトチェック開始")
    print(f"  文字数: {len(text)}文字")
    print(f"{'=' * 60}")
    print("\nAIエージェントが検証中です...")
    print("（複数のAIが独立して検証するため、数分かかります）\n")

    try:
        from crew import FactCheckCrew
        result = FactCheckCrew().run(text=text)
    except Exception as e:
        print(f"\n[エラー] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  検証完了！")
    print("=" * 60)
    print(result)

    if input("\nファイルに保存しますか？ (y/n): ").strip().lower() == "y":
        filename = save_result(result)
        print(f"保存しました: {filename}")


if __name__ == "__main__":
    main()
