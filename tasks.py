import os
# import subprocess # invokeのc.runを使用するため基本的に不要
# import argparse # invoke を使うので argparse は不要
import requests
from dotenv import load_dotenv, find_dotenv # ★ find_dotenv もインポート ★
import json
from invoke import task # invoke の task をインポート
from datetime import datetime, timezone # test_create_employee_event で必要

# ★ --- DEBUG --- デバッグ用に追加 --- ★
# .env ファイルを探し、見つかったパスを表示してから読み込む
dotenv_path = find_dotenv()
if dotenv_path: # 見つかった場合のみ読み込む
    print(f"Loading .env file from: {dotenv_path}")
    load_dotenv(dotenv_path)
else:
    print("Warning: .env file not found, using default settings or environment variables.")


# --- デフォルト変数の設定 ---
# 環境変数から取得し、なければデフォルト値を使用 (Makefileの ?= に相当)
API_BASE_URL = os.getenv('API_BASE_URL', 'http://127.0.0.1:5000') # ポートを5000に統一
PROD_API_BASE_URL = os.getenv('PROD_API_BASE_URL') # 本番用URLは環境変数での設定を推奨
SECRET_AUTH_KEY = os.getenv('SECRET_AUTH_KEY', 'mysecretkey_dev_default') # 開発用デフォルトキー

# テスト用JSONデータ (文字列として定義)
TEST_ITEM_DATA_STR = os.getenv('TEST_ITEM_DATA', "{\"message\": \"This is a default test message from tasks.py\"}")


# --- 各タスクを関数として定義 ---

@task
def setup(c): # invokeタスクはコンテキスト 'c' を受け取る
    """依存パッケージをインストールします"""
    print("Installing dependencies from requirements.txt...")
    try:
        result = c.run('pip install -r requirements.txt', hide=False) # hide=Falseで出力表示
        if result.ok:
            print("Setup complete.")
        else:
            print(f"Error during pip install. Exit code: {result.return_code}")
    except Exception as e: # c.runが予期せぬエラーを出した場合 (例: pipコマンドがない)
        print(f"Failed to run pip install: {e}")
        print("Ensure Python and pip are installed and in your PATH, or your virtual environment is activated.")

@task
def run_server(c): # invokeタスクはコンテキスト 'c' を受け取る
    """Flask開発サーバーを起動します"""
    port = API_BASE_URL.split(':')[-1] if ':' in API_BASE_URL else '5000' # URLからポートを抽出
    print(f"Starting Flask development server at http://0.0.0.0:{port}...")
    
    env_vars = os.environ.copy()
    env_vars['FLASK_APP'] = 'app.py'
    env_vars['FLASK_ENV'] = 'development' 
    env_vars['SECRET_AUTH_KEY'] = str(SECRET_AUTH_KEY) if SECRET_AUTH_KEY is not None else ''
    # Datastore接続に必要な環境変数が .env から読み込まれていることを期待
    # もし `GOOGLE_APPLICATION_CREDENTIALS` を明示的に渡したい場合は以下をアンコメント
    # if os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
    # env_vars['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

    try:
        # pty=True は Unix系OSでCtrl+Cでの停止をうまく処理するために役立ちます
        # Windowsでは動作が異なる場合があるので注意
        c.run(f'flask run --host=0.0.0.0 --port={port}', env=env_vars, pty=True)
    except Exception as e: 
         print(f"Error starting Flask server: {e}")
         print("Ensure Flask is installed (run 'invoke setup') and virtual environment is activated.")


# ヘルパー関数：POSTリクエストを送信する (requestsライブラリ使用)
# この関数は invoke タスクではないので @task は不要
def _send_post_request(base_url_for_req, endpoint, data_str_to_send, auth_key_for_req):
    """POSTリクエストを送信するヘルパー関数 (requests使用)"""
    url = f"{base_url_for_req}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Key": auth_key_for_req
    }
    
    try:
        # ★ json.loads の呼び出しはここ（ヘルパー関数内）★
        data_dict = json.loads(data_str_to_send)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON data: {e}")
        # --- DEBUG --- エラー発生時にも文字列を再出力 ---
        print(f"Problematic string was: ->{data_str_to_send}<-")
        # -------------
        return None # JSONが無効なら処理を中断

    print(f"Sending POST request to {url} using requests library")
    # print(f"Headers: {headers}") # 機密情報(Auth-Key)を含む可能性があるので、デバッグ時以外は注意
    print(f"Data (original string): {data_str_to_send}") # 送信する元の文字列を表示

    try:
        # requests ライブラリを使ってPOSTリクエストを送信
        # ★ json=data_dict で辞書形式を渡す ★
        response = requests.post(url, headers=headers, json=data_dict)
        response.raise_for_status() # HTTPエラー（4xx, 5xx）が発生した場合に例外を発生させる

        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
        return response # 成功した場合はresponseオブジェクトを返す

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None # リクエスト自体が失敗した場合

    finally:
        print("-" * 20) # 区切り線


@task
def test_post_data_auth_local(c): # invokeタスクはコンテキスト 'c' を受け取る
    """Test POST /data with auth (local API_BASE_URL) using requests library"""
    print(f"--- Testing POST /data to LOCAL ({API_BASE_URL}) ---")
    if not SECRET_AUTH_KEY:
        print("Error: SECRET_AUTH_KEY is not set. Aborting test.")
        return
    _send_post_request(API_BASE_URL, '/data', TEST_ITEM_DATA_STR, SECRET_AUTH_KEY)

@task
def test_post_data_auth_prod(c): # invokeタスクはコンテキスト 'c' を受け取る
    """Test POST /data with auth (PROD_API_BASE_URL) using requests library"""
    if not PROD_API_BASE_URL:
        print("Error: PROD_API_BASE_URL is not set. This test requires PROD_API_BASE_URL in .env or environment. Aborting test.")
        return
    # 本番環境用の認証キーは .env などで別途 PROD_SECRET_AUTH_KEYとして設定することを推奨
    prod_auth_key = os.getenv('PROD_SECRET_AUTH_KEY', SECRET_AUTH_KEY) 
    if not prod_auth_key:
        print("Error: PROD_SECRET_AUTH_KEY (or fallback SECRET_AUTH_KEY) is not set. Aborting test.")
        return
    print(f"--- Testing POST /data to PROD ({PROD_API_BASE_URL}) ---")
    _send_post_request(PROD_API_BASE_URL, '/data', TEST_ITEM_DATA_STR, prod_auth_key)

# test_create_employee_event で使用する定数
TEST_EMPLOYEE_ID_FOR_EVENT_TESTS = "test_emp_for_event_001"

# この関数は invoke タスクではないので @task は不要
def _ensure_test_employee_exists(c, employee_id_to_check, current_api_base_url, auth_key_for_req):
    """テスト用の従業員が存在することを確認し、なければ作成するヘルパー関数 (curl使用)"""
    print(f"Checking if employee '{employee_id_to_check}' exists for event testing at {current_api_base_url}...")
    check_url = f"{current_api_base_url}/employees/{employee_id_to_check}"
    
    res = c.run(f"curl -s -o /dev/null -w \"%{{http_code}}\" -X GET -H \"X-Auth-Key: {auth_key_for_req}\" {check_url}", hide=True, warn=True)
    
    if res.stdout.strip() == "200":
        print(f"Employee '{employee_id_to_check}' found.")
        return True
    
    print(f"Employee '{employee_id_to_check}' not found. Attempting to create...")
    employee_data = {
        "name": f"Event Test Dummy {employee_id_to_check}",
        "email": f"{employee_id_to_check.replace('_', '-')}@example.com", # Ensure valid email format
        "role": "Event Test Subject",
        "delete_flag": False
    }
    create_url = f"{current_api_base_url}/employees/{employee_id_to_check}"
    create_res = c.run(f"curl -s -w \"\\n%{{http_code}}\" -X POST -H \"Content-Type: application/json\" -H \"X-Auth-Key: {auth_key_for_req}\" -d '{json.dumps(employee_data)}' {create_url}", hide=True, warn=True)
    
    try:
        create_stdout_body, create_status_code = create_res.stdout.rsplit("\n", 1)
    except ValueError: 
        print(f"Failed to parse response from employee creation for {employee_id_to_check}. stdout: {create_res.stdout}")
        return False

    if create_status_code == "201" or create_status_code == "409": 
        print(f"Employee '{employee_id_to_check}' created or already existed (HTTP {create_status_code}).")
        return True
    else:
        print(f"Failed to create employee '{employee_id_to_check}'. Status: {create_status_code}, Response: {create_stdout_body}")
        return False


@task
def test_create_employee_event(c): # invokeタスクはコンテキスト 'c' を受け取る
    """Test POST /employees/<employee_id>/events endpoint (Normal cases only). Uses curl."""
    print(f"\n--- Testing Event Creation (POST /employees/<employee_id>/events) - Normal Cases Only ---")
    
    # ファイルスコープの API_BASE_URL と SECRET_AUTH_KEY を使用
    if not SECRET_AUTH_KEY: 
        print("Error: SECRET_AUTH_KEY is not set. Aborting test.")
        return

    # 0. テスト用従業員の準備
    if not _ensure_test_employee_exists(c, TEST_EMPLOYEE_ID_FOR_EVENT_TESTS, API_BASE_URL, SECRET_AUTH_KEY):
        print(f"Failed to ensure test employee '{TEST_EMPLOYEE_ID_FOR_EVENT_TESTS}' exists. Aborting event creation tests.")
        return
    
    employee_id = TEST_EMPLOYEE_ID_FOR_EVENT_TESTS
    base_event_url = f"{API_BASE_URL}/employees/{employee_id}/events" 

    common_headers_curl = f"-H \"Content-Type: application/json\" -H \"X-Auth-Key: {SECRET_AUTH_KEY}\""

    # 1. 正常系: 必須項目のみ
    print("\n[Case 1.1] Create event with only required fields")
    payload1 = {
        "event_type": "日常業務",
        "description": "定例ミーティングに参加し、タスク進捗を報告した。"
    }
    cmd1 = f"curl -s -w \"\\n%{{http_code}}\" -X POST {common_headers_curl} -d '{json.dumps(payload1)}' {base_event_url}"
    res1 = c.run(cmd1, hide=False) 
    body1, code1 = res1.stdout.rsplit("\n", 1)
    assert code1 == "201", f"Case 1.1 Failed: Expected 201, got {code1}. Body: {body1}"
    try:
        data1 = json.loads(body1)
        assert "event_id" in data1
        assert data1["employee_id"] == employee_id
        assert data1["event_type"] == payload1["event_type"]
        assert data1["description"] == payload1["description"]
        assert "timestamp" in data1 
        assert data1.get("details") is None
        print(f"Case 1.1 PASSED. Event ID: {data1['event_id']}")
    except (json.JSONDecodeError, AssertionError) as e:
        print(f"Case 1.1 FAILED validation: {e}. Body: {body1}")
        assert False 

    # 2. 正常系: timestamp と details を含む
    print("\n[Case 1.2] Create event with timestamp and details")
    ts_string = datetime.now(timezone.utc).isoformat() 
    payload2 = {
        "timestamp": ts_string,
        "event_type": "技術研修",
        "description": "新しいフレームワークのオンライン研修を受講した。",
        "details": {"framework_name": "FutureFrameX", "duration_hours": 3, "completed": True}
    }
    cmd2 = f"curl -s -w \"\\n%{{http_code}}\" -X POST {common_headers_curl} -d '{json.dumps(payload2)}' {base_event_url}"
    res2 = c.run(cmd2, hide=False)
    body2, code2 = res2.stdout.rsplit("\n", 1)
    assert code2 == "201", f"Case 1.2 Failed: Expected 201, got {code2}. Body: {body2}"
    try:
        data2 = json.loads(body2)
        assert data2["event_id"] is not None
        assert data2["timestamp"] == ts_string 
        assert data2["details"]["framework_name"] == "FutureFrameX"
        print(f"Case 1.2 PASSED. Event ID: {data2['event_id']}")
    except (json.JSONDecodeError, AssertionError) as e:
        print(f"Case 1.2 FAILED validation: {e}. Body: {body2}")
        assert False

    print("\n--- Event Creation Tests (Normal Cases Only) Completed ---")

# invoke は __main__ ブロックや argparse のコードを必要としません。
# このファイル (tasks.py) がカレントディレクトリにある状態で、
# ターミナルから 'invoke <タスク名>' (例: 'invoke setup', 'invoke run-server', 'invoke test-create-employee-event')
# のように実行します。
# 利用可能なタスクの一覧は 'invoke --list' で確認できます。