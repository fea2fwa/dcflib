import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import sys

def scrape_dell_community(url):
    """
    指定されたURLからDell Communityの投稿情報を抽出する関数
    """
    try:
        # 指定したURLにアクセスし、HTMLコンテンツを取得
        response = requests.get(url)
        # ステータスコードが200番台でない場合は例外を発生させる
        response.raise_for_status()

        # BeautifulSoupオブジェクトを作成し、HTMLをパース
        soup = BeautifulSoup(response.text, 'html.parser')

        # --- タイトルの取得 ---
        title_element = soup.find('h1', class_='conversation-balloon__content__title')
        title = title_element.get_text(strip=True) if title_element else "タイトルが見つかりません"

        # --- 投稿者名の取得 ---
        # 質問コンテナ内のユーザー情報を探す
        question_author_container = soup.find('div', class_='balloon__user')
        question_author = "質問者が見つかりません"
        if question_author_container:
            question_author_element = question_author_container.find('p', class_='text-overflow')
            if question_author_element:
                question_author = question_author_element.get_text(strip=True)

        # --- ページビュー数の取得 ---
        view_count_container = soup.find('div', class_='dell-conversation-balloon__view-count-cnt')
        if view_count_container:
            view_count_element = view_count_container.find('p', class_='text--small')
            page_views = view_count_element.get_text(strip=True) if view_count_element else "ページビュー数が見つかりません"
        else:
            page_views = "ページビュー数が見つかりません"

        # --- 投稿日時の取得（GMT）---
        post_date_element = soup.find('p', class_='dell-conversation-ballon__header-date')
        post_date = post_date_element.get_text(strip=True) if post_date_element else "投稿日時が見つかりません"

        # --- Solved!マークがついているかを確認 ---
        solved_element = soup.find('p', class_='conversation-balloon-dell__solved-label', string='Solved!')
        # Solved!マークの有無をYes/Noで表現
        if solved_element:
            solved = "Yes"
        else:
            solved = "No"

        # --- 質問文のテキストを取得 ---
        init_body_element = soup.find('div', class_='conversation-balloon__content__text')
        init_body = init_body_element.get_text(separator='\n', strip=True) if init_body_element else "質問文が見つかりません"

        # --- 回答部分の抽出 ---
        # 回答をまとめるリストを準備
        comments_list = []
        # すべてのコメント（回答）のコンテナを取得
        comment_list = soup.find_all('div', class_='comment-list__comment')

        print("--- 回答 ---")
        if not comment_list:
            print("回答はありません。")
        else:
            # 各回答をループ処理
            for i, comment in enumerate(comment_list, 1):
                # 投稿者
                author_element = comment.find('p', class_='text-overflow')
                author = author_element.get_text(strip=True) if author_element else "投稿者不明"
                
                # 投稿日時
                comment_date_element = comment.find('p', class_='dell-comment-ballon__header-date')
                comment_date = comment_date_element.get_text(strip=True) if comment_date_element else "投稿日時不明"

                # Acceptedマーク
                comm_accepted_comment_element = comment.find('use', attrs={'xlink:href': '#icon-dell_community_accepted_solution_clr'})
                dell_accepted_comment_element = comment.find('use', attrs={'xlink:href': '#icon-dell_accepted_solution_clr'})
                # Community Acceptedの場合はYes、Dell Employee Acceptedの場合はYes-Dell、AcceptedマークがついていないものはNoを設定
                if comm_accepted_comment_element:
                    accepted = "Yes"
                elif dell_accepted_comment_element:
                    accepted = "Yes-Dell"
                else:
                    accepted = "No"            
                
                # 回答本文
                comment_body_element = comment.find('div', class_='dell-comment-balloon__content__text')
                comment_body = comment_body_element.get_text(separator='\n', strip=True) if comment_body_element else "本文がありません"

                # 抽出した情報を辞書にまとめる
                comment_data = {
                    'author': author,
                    'date': comment_date,
                    'accepted': accepted,
                    'body': comment_body
                }
                # リストに辞書を追加
                comments_list.append(comment_data)


        return {
            "url": url,
            "title": title,
            "question_author": question_author,
            "page_views": page_views,
            "solved": solved,
            "init_body": init_body,
            "comments": comments_list
        }

    except requests.exceptions.RequestException as e:
        return {"url": url, "error": f"URLへのアクセス中にエラーが発生しました: {e}"}
    except Exception as e:
        return {"url": url, "error": f"予期せぬエラーが発生しました: {e}"}

def main():
    """
    コマンドライン引数で指定されたファイルからURLを読み込み、各URLの情報を抽出して表示し、JSONファイルに書き出す
    """
    if len(sys.argv) < 2:
        print("使用法: python scraping.py <URL/threadIDリストtxtファイル名>")
        sys.exit(1)

    input_filename = sys.argv[1]

    try:
        base_url = "https://www.dell.com/community/en/conversations/x//"
        with open(input_filename, "r", encoding="utf-8") as f:
            urls = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if not line.startswith("http"):
                    line = base_url + line
                urls.append(line)

        all_data = []
        for url in urls:
            data = scrape_dell_community(url)
            all_data.append(data)
            print("--- 抽出結果 ---")
            if "error" in data:
                print(f"URL: {data['url']}")
                print(f"エラー: {data['error']}")
            else:
                print(f"URL: {data['url']}")
                print(f"タイトル: {data['title']}")
                print(f"投稿者: {data['question_author']}")
                print(f"ページビュー数: {data['page_views']}")
                print(f"Solved!マーク: {data['solved']}")
                print("\n--- Thread本文 ---")
                print(data['init_body'])
                print("\n--- Commentリスト ---")
                print(data['comments'])
            print("\n" + "="*50 + "\n")

        # ファイル名の生成
        date_str = datetime.now().strftime("%y%m%d%H%M")
        output_filename = f"dcfcontents_{date_str}.json"

        # JSONファイルへの書き出し
        with open(output_filename, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=4)
        
        print(f"データが {output_filename} に保存されました。")

    except FileNotFoundError:
        print(f"{input_filename}が見つかりません。")
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
