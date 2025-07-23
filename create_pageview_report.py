import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import sys
import os
import re

def scrape_title_and_views(url):
    """
    指定されたURLからスレッドタイトルとページビュー数を抽出する関数
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # --- タイトルの取得 ---
        title_element = soup.find('h1', class_='conversation-balloon__content__title')
        if title_element:
            # get_text()を使い、タグ内のテキストをスペース区切りで結合し、空白を正規化する
            title_text = title_element.get_text(separator=' ', strip=True)
            # 改行等をスペースに置換し、連続するスペースを1つにまとめる
            title = ' '.join(title_text.split())
        else:
            title = "タイトル不明"

        # --- ページビュー数の取得 ---
        view_count_text = "0" # デフォルト値
        view_count_container = soup.find('div', class_='dell-conversation-balloon__view-count-cnt')
        if view_count_container:
            view_count_element = view_count_container.find('p', class_='text--small')
            if view_count_element:
                # "XXX views" から数字のみを抽出
                view_count_text = ''.join(filter(str.isdigit, view_count_element.get_text(strip=True)))

        return {"url": url, "title": title, "views": int(view_count_text)}

    except requests.exceptions.RequestException as e:
        print(f"エラー: {url} の取得に失敗しました: {e}")
        return None
    except Exception as e:
        print(f"エラー: {url} の処理中に予期せぬエラーが発生しました: {e}")
        return None

def main():
    """
    URLリストファイルを読み込み、各URLのページビュー数を時系列でTSVファイルに記録する
    """
    if len(sys.argv) < 2:
        print("使用法: python create_pageview_report.py <URLリストファイル名>")
        sys.exit(1)

    input_filename = sys.argv[1]
    output_tsv_filename = "dcf_pageviews.tsv"

    # --- URLリストの読み込み (正規表現で堅牢化) ---
    url_pattern = re.compile(r'(https?://www\.dell\.com/community/[^\s	"]+)')
    urls = set()
    try:
        with open(input_filename, "r", encoding="utf-8") as f:
            for line in f:
                match = url_pattern.search(line)
                if match:
                    urls.add(match.group(1))
    except FileNotFoundError:
        print(f"エラー: {input_filename} が見つかりません。")
        sys.exit(1)

    if not urls:
        print("入力ファイルから有効なURLが見つかりませんでした。")
        sys.exit(0)

    # --- 既存TSVの読み込み ---
    try:
        # URLをインデックスとして読み込む
        df = pd.read_csv(output_tsv_filename, sep='	', index_col='url')
    except (FileNotFoundError, pd.errors.EmptyDataError):
        # ファイルがない、または空の場合は新規作成
        df = pd.DataFrame(columns=['title'])
        df.index.name = 'url'

    # --- スクレイピングとデータ更新 ---
    timestamp_col = datetime.now().strftime('%Y-%m-%d_%H-%M')
    print(f"{len(urls)} 件のURLを処理します...")

    for url in sorted(list(urls)):
        print(f"処理中: {url}")
        data = scrape_title_and_views(url)
        if data:
            # .locを使ってURLをキーにデータを更新または追加
            df.loc[data['url'], 'title'] = data['title']
            df.loc[data['url'], timestamp_col] = data['views']

    # --- データ型の整理 ---
    # title以外の列（タイムスタンプ列）を数値型に変換
    for col in df.columns:
        if col != 'title':
            # errors='coerce'は変換できない値をNaNにする
            df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')

    # --- 不要な行の削除 ---
    # タイムスタンプ列を特定
    time_cols_for_dropna = [c for c in df.columns if c != 'title']
    # タイムスタンプ列のすべてがNaNである行を削除
    if time_cols_for_dropna: # タイムスタンプ列が存在する場合のみ実行
        original_rows = len(df)
        df.dropna(subset=time_cols_for_dropna, how='all', inplace=True)
        dropped_rows = original_rows - len(df)
        if dropped_rows > 0:
            print(f"ページビューの記録が一度もない {dropped_rows} 件の行を削除しました。")

    # --- 古い列の削除 ---
    # タイムスタンプ列を特定し、古い順にソート
    time_cols = sorted([c for c in df.columns if c != 'title'])
    
    # 列数が100を超えていたら、超過分を古い順に削除
    MAX_COLS = 2
    if len(time_cols) > MAX_COLS:
        num_to_drop = len(time_cols) - MAX_COLS
        cols_to_drop = time_cols[:num_to_drop]
        print(f"タイムスタンプ列が{len(time_cols)}列になったため、最も古い{num_to_drop}列を削除します: {', '.join(cols_to_drop)}")
        df.drop(columns=cols_to_drop, inplace=True)

    # --- TSVファイルへの書き出し ---
    try:
        # urlをインデックスから列に戻す
        df.reset_index(inplace=True)
        
        # 列の順序を整理 (url, title, 古い日付..., 新しい日付...)
        final_time_cols = sorted([c for c in df.columns if c not in ['url', 'title']])
        final_cols = ['url', 'title'] + final_time_cols
        df = df[final_cols]

        df.to_csv(output_tsv_filename, index=False, sep='	', encoding='utf-8-sig')
        print(f"\n処理が完了しました。データが {output_tsv_filename} に保存されました。")
    except Exception as e:
        print(f"エラー: TSVファイルへの書き込み中にエラーが発生しました: {e}")

if __name__ == "__main__":
    main()