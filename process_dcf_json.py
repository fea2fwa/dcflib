import json
import argparse
import datetime
import os
import re

def classify_by_keyword(text):
    """
    テキスト内のキーワードに基づいてカテゴリを判定する簡易的な分類器。
    """
    # 各カテゴリのキーワードを正規表現で定義
    spec_kws = r"仕様|詳細|スペック|機能"
    config_kws = r"構成|設定|サポート|ベストプラクティス|インストール|導入|構築"
    ops_kws = r"方法|how-to|手順|操作|実行|コマンド"
    bf_kws = r"問題|エラー|解決|失敗|トラブル|不具合|修正|break|fix"

    # キーワードのマッチ数をカウント
    scores = {
        "Specifications": len(re.findall(spec_kws, text, re.IGNORECASE)),
        "Configurations": len(re.findall(config_kws, text, re.IGNORECASE)),
        "Operations": len(re.findall(ops_kws, text, re.IGNORECASE)),
        "Break&Fix": len(re.findall(bf_kws, text, re.IGNORECASE)),
    }

    # 最もスコアの高いカテゴリを返す（スコアが0の場合はデフォルト）
    if all(score == 0 for score in scores.values()):
        return "Operations"  # デフォルトカテゴリ

    return max(scores, key=scores.get)


def generate_summary_and_category(text):
    """
    テキストを受け取り、要約とカテゴリを生成する。

    【注】
    この関数は現在、単純な文字数制限とキーワードベースの分類を行っています。
    より高精度な要約・分類のためには、この部分を
    OpenAI GPTシリーズなどの大規模言語モデル（LLM）APIへのリクエスト処理に
    置き換えることを強く推奨します。
    """
    # 1. 要約を生成する（現在は単純な切り出し）
    # LLMに置き換える部分:
    # response = openai.Completion.create(
    #   model="text-davinci-003",
    #   prompt=f"以下のテキストを20文字と80文字で要約してください。\n\n{text}",
    #   ...
    # )
    # short_summary = response.choices[0].text.strip()[:20]
    # summary = response.choices[0].text.strip()[:80]
    
    cleaned_text = text.replace('\n', ' ').replace('\r', '')
    short_summary = cleaned_text[:20]
    summary = cleaned_text[:80]

    # 2. カテゴリを分類する
    # LLMに置き換えるか、より洗練された分類器を使用する部分
    category = classify_by_keyword(text)

    return short_summary, summary, category


def process_json_file(file_path):
    """
    指定されたJSONファイルを処理し、要約とカテゴリを追加して出力する。
    入力JSONは単一のオブジェクト、またはオブジェクトのリストに対応。
    """
    # 1. JSONファイルを読み込む
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data_in = json.load(f)
            print(type(data_in))
    except FileNotFoundError:
        print(f"エラー: ファイルが見つかりません: {file_path}")
        return
    except json.JSONDecodeError:
        print(f"エラー: JSONの形式が正しくありません: {file_path}")
        return

    # 入力データが単一オブジェクトの場合、リストに変換して統一的に処理
    if not isinstance(data_in, list):
        items_to_process = [data_in]
    else:
        items_to_process = data_in

    processed_items = []
    for item in items_to_process:
        # 2. テキスト情報を抽出・結合
        text_parts = []
        if item.get('title'):
            text_parts.append(item['title'])
        if item.get('init_body'):
            text_parts.append(item['init_body'])
        if isinstance(item.get('comments'), list):
            for comment in item['comments']:
                if comment.get('body'):
                    text_parts.append(comment['body'])
        full_text = "\n".join(text_parts)

        if not full_text:
            print(f"警告: 項目（title: {item.get('title', 'N/A')}）には処理対象のテキストがありません。スキップします。")
            continue

        # 3. サマリ生成とカテゴリ分類
        short_summary, summary, thread_type = generate_summary_and_category(full_text)

        # 4. 元のデータに新しい項目を追加
        item['short_summary'] = short_summary
        item['summary'] = summary
        item['thread_type'] = thread_type
        processed_items.append(item)

    if not processed_items:
        print("処理対象の項目がありませんでした。")
        return
    
    # JSONファイルを書き込むディレクトリを指定
    JSON_DIR = "jsonfiles"

    # 5. ファイルに出力
    # 5-1. 日付ごとのファイルに出力
    date_str = datetime.datetime.now().strftime('%Y%m%d')
    output_filename = os.path.join(JSON_DIR, f"dcfcontents_full_{date_str}.json")
    # output_filename = f"dcfcontents_full_{date_str}.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(processed_items, f, ensure_ascii=False, indent=4)
    print(f"処理結果を {output_filename} に保存しました。")

    # 5-2. 全件ファイルに追記
    all_filename = os.path.join(JSON_DIR, "dcfcontents_full_all.json")
    all_data = []
    if os.path.exists(all_filename):
        with open(all_filename, 'r', encoding='utf-8') as f:
            try:
                content = f.read()
                if content:
                    all_data = json.loads(content)
                if not isinstance(all_data, list):
                    print(f"警告: {all_filename} の内容がリスト形式ではありません。ファイルを初期化します。")
                    all_data = []
            except json.JSONDecodeError:
                print(f"警告: {all_filename} のJSON解析に失敗しました。ファイルを初期化します。")
                all_data = []

    # 既存データと重複しない項目のみを追記
    new_items_count = 0
    for new_item in processed_items:
        is_new = True
        if new_item.get('url') and new_item.get('title'):
            for existing_item in all_data:
                if existing_item.get('url') == new_item['url'] and existing_item.get('title') == new_item['title']:
                    is_new = False
                    break
        if is_new:
            all_data.append(new_item)
            new_items_count += 1

    if new_items_count > 0:
        with open(all_filename, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=4)
        print(f"{all_filename} に {new_items_count} 件の新しい項目を追記しました。")
    else:
        print(f"{all_filename} に追記する新しい項目はありませんでした。")


def main():
    """
    メイン処理。コマンドライン引数を解析し、ファイル処理を実行する。
    """
    # JSONファイルを保存するディレクトリの存在を確認
    JSON_DIR = "jsonfiles"
    os.makedirs(JSON_DIR, exist_ok=True)

    parser = argparse.ArgumentParser(
        description="DCFのJSONファイルを読み込み、要約とカテゴリ分類を追加して出力します。",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('json_file', help=f"処理対象のJSONファイル名（{JSON_DIR}/内）")
    args = parser.parse_args()

    process_json_file(args.json_file)

if __name__ == '__main__':
    main()
