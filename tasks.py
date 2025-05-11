import os
import subprocess
import argparse
import requests
from dotenv import load_dotenv, find_dotenv # ★ find_dotenv もインポート ★
import json

# ★ --- DEBUG --- デバッグ用に追加 --- ★
# .env ファイルを探し、見つかったパスを表示してから読み込む
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

# --- デフォルト変数の設定 ---
# 環境変数から取得し、なければデフォルト値を使用 (Makefileの ?= に相当)
API_BASE_URL = os.getenv('API_BASE_URL', 'http://127.0.0.1:5000')
SECRET_AUTH_KEY = os.getenv('SECRET_AUTH_KEY', 'mysecretkey')

# テスト用JSONデータ (文字列として定義)
TEST_ITEM_DATA_STR = "{\"message\": \"This is a hardcoded test message\"}"


# --- 各タスクを関数として定義 ---

def setup():
    """依存パッケージをインストールします"""
    print("Installing dependencies...")
    # subprocessを使って pip コマンドを実行
    # check=True でコマンド失敗時に例外を発生させる
    try:
        subprocess.run(['pip', 'install', '-r', 'requirements.txt'], check=True)
        print("Setup complete.")
    except FileNotFoundError:
        print("Error: 'pip' command not found. Ensure Python and pip are installed and in PATH, or virtual environment is activated.")
    except subprocess.CalledProcessError as e:
        print(f"Error during pip install: {e}")
        print(f"Command output: {e.stdout.decode()} {e.stderr.decode()}")


def run_server():
    """Flask開発サーバーを起動します"""
    print(f"Starting Flask development server at {API_BASE_URL}...")
    # Flaskサーバー起動に必要な環境変数を設定
    # os.environ.copy() で現在の環境変数を引き継ぎつつ、必要な変数を上書き/追加
    env_vars = os.environ.copy()
    env_vars['FLASK_APP'] = 'app.py'
    env_vars['FLASK_ENV'] = 'development'
    # SECRET_AUTH_KEY が None の場合に備え str() で文字列化しておく
    env_vars['SECRET_AUTH_KEY'] = str(SECRET_AUTH_KEY) if SECRET_AUTH_KEY is not None else ''

    # subprocessを使って flask run コマンドを実行
    # run_server タスクが実行されている間、サーバーが起動し続ける
    # Ctrl+C で停止可能
    try:
        # shell=True はWindowsでactivateスクリプトをsourceする場合などに便利ですが、
        # flask run のように直接実行する場合は不要な場合が多いです。
        # 問題がなければ shell=False のままの方が安全です。
        subprocess.run(['flask', 'run', '--host=0.0.0.0', '--port=5000'], env=env_vars)
    except FileNotFoundError:
         print("Error: 'flask' command not found. Ensure Flask is installed (run 'python tasks.py setup') and virtual environment is activated.")


# ヘルパー関数：POSTリクエストを送信する
# この関数内でjson.loadsとrequests.postを実行する
def _send_post_request(base_url, endpoint, data_str, auth_key):
    """POSTリクエストを送信するヘルパー関数"""
    url = f"{base_url}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Key": auth_key
    }
    # JSON文字列をPython辞書に変換


    try:
        # ★ json.loads の呼び出しはここ（ヘルパー関数内）★
        data = json.loads(data_str)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON data: {e}")
        print("Please ensure TEST_ITEM_DATA in .env is valid JSON string (using double quotes for keys/values).")
        # --- DEBUG --- エラー発生時にも文字列を再出力 ---
        print(f"Problematic string was: ->{data_str}<-")
        # -------------
        return None # JSONが無効なら処理を中断

    print(f"Sending POST request to {url}")
    # print(f"Headers: {headers}") # 機密情報(Auth-Key)を含む可能性があるので、デバッグ時以外は注意
    print(f"Data: {data_str}") # 送信する元の文字列を表示

    try:
        # requests ライブラリを使ってPOSTリクエストを送信
        # ★ json=data で辞書形式を渡す ★
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status() # HTTPエラー（4xx, 5xx）が発生した場合に例外を発生させる

        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
        return response # 成功した場合はresponseオブジェクトを返す

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None # リクエスト自体が失敗した場合

    finally:
         print("-" * 20) # 区切り線


# APIテストタスク：/dataエンドポイントに認証付きでPOSTテスト
# このタスク関数はヘルパー関数を呼び出すだけ
def test_post_data_auth():
    _send_post_request(API_BASE_URL, '/data', TEST_ITEM_DATA_STR, SECRET_AUTH_KEY)


# --- コマンドライン引数の解析とタスク実行 ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Project task runner using Python.")
    # dest="command" で、実行されたサブコマンド名が args.command に格納される
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # setup コマンドの定義
    # set_defaults() で、このサブコマンドが選ばれた場合にどの関数を呼び出すかを指定
    setup_parser = subparsers.add_parser("setup", help="Install dependencies from requirements.txt")
    setup_parser.set_defaults(func=setup) # setupコマンド実行時はsetup()関数を呼び出す

    # run コマンドの定義
    run_parser = subparsers.add_parser("run", help="Start the Flask development server")
    run_parser.set_defaults(func=run_server) # runコマンド実行時はrun_server()関数を呼び出す

    # test-post-data-auth コマンドの定義
    test_data_parser = subparsers.add_parser("test-post-data-auth", help="Test POST /data with auth")
    test_data_parser.set_defaults(func=test_post_data_auth) # test-post-data-auth実行時はtest_post_data_auth()関数を呼び出す

    args = parser.parse_args()

    # args.command が None の場合はサブコマンドが指定されていない（つまりヘルプ表示）
    # args.func には set_defaults() で設定された関数が入っている
    if hasattr(args, 'func'):
        args.func() # 対応する関数を実行
    else:
        # コマンドが指定されない場合や不明な場合、ヘルプを表示
        parser.print_help()