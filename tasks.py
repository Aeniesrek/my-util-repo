import os
import requests
from dotenv import load_dotenv, find_dotenv
import json
from invoke import task
from datetime import datetime, timezone

# .env ファイルの読み込み
dotenv_path = find_dotenv()
if dotenv_path:
    print(f"Loading .env file from: {dotenv_path}")
    load_dotenv(dotenv_path)
else:
    print("Warning: .env file not found, using default settings or environment variables.")

# --- グローバル設定 ---
API_BASE_URL = os.getenv('API_BASE_URL', 'http://127.0.0.1:5000')
PROD_API_BASE_URL = os.getenv('PROD_API_BASE_URL')
SECRET_AUTH_KEY = os.getenv('SECRET_AUTH_KEY', 'mysecretkey_dev_default')
TEST_ITEM_DATA_STR = os.getenv('TEST_ITEM_DATA', "{\"message\": \"This is a default test message\"}")
TEST_EMPLOYEE_ID = "test_emp_001" 

# --- APIリクエスト ヘルパー ---

def _send_request(method, base_url, endpoint, auth_key=None, data_str=None, params=None):
    """HTTPリクエストを送信する共通ヘルパー (requests使用)"""
    if not base_url:
        print(f"Error: Base URL for {endpoint} is not configured.")
        return None
        
    url = f"{base_url}{endpoint}"
    headers = {}
    if auth_key:
        headers["X-Auth-Key"] = auth_key
    
    json_data = None
    if data_str:
        try:
            json_data = json.loads(data_str)
            headers["Content-Type"] = "application/json"
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}. Data: ->{data_str}<-")
            return None 

    print(f"Sending {method.upper()} request to {url}...")
    try:
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, json=json_data, params=params)
        else:
            print(f"Unsupported HTTP method: {method}")
            return None
        return response
    except requests.exceptions.RequestException as e:
        print(f"Request to {url} failed: {e}")
        return None
    finally:
        print("-" * 20)

def _send_get_request(base_url, endpoint, auth_key=None, params=None):
    return _send_request("GET", base_url, endpoint, auth_key=auth_key, params=params)

def _send_post_request(base_url, endpoint, data_str, auth_key=None, params=None):
    return _send_request("POST", base_url, endpoint, auth_key=auth_key, data_str=data_str, params=params)

# --- テスト用ヘルパー (Employee Eventテストでは引き続き使用) ---

def _ensure_test_employee_exists(c, employee_id, api_url, auth_key):
    """テスト用従業員の存在確認・作成 (requests使用) -主にイベントテストの前提として使用"""
    print(f"Ensuring test employee '{employee_id}' exists at {api_url} for subsequent tests...")
    check_endpoint = f"/employees/{employee_id}"
    response = _send_get_request(api_url, check_endpoint, auth_key)
    
    if response and response.status_code == 200:
        print(f"Employee '{employee_id}' found.")
        return True
    elif response and response.status_code == 404:
        print(f"Employee '{employee_id}' not found. Attempting to create for subsequent tests...")
    elif response:
        print(f"Failed to check employee '{employee_id}': Status {response.status_code}. Aborting ensure step.")
        return False
    else:
        print(f"Failed to check employee '{employee_id}' (request failed). Aborting ensure step.")
        return False
        
    employee_data = { # このペイロードは ensure のためのもの
        "name": f"Test Dummy (for events) {employee_id}",
        "email": f"{employee_id.replace('_', '.')}@example.com", # Ensure valid email
        "role": "Event Test Prerequisite", "delete_flag": False
    }
    create_response = _send_post_request(api_url, f"/employees/{employee_id}", json.dumps(employee_data), auth_key)
    
    if create_response and (create_response.status_code == 201 or create_response.status_code == 409):
        print(f"Employee '{employee_id}' ensured (created/already existed: HTTP {create_response.status_code}).")
        return True
    else:
        status = create_response.status_code if create_response else "N/A"
        print(f"Failed to ensure (create) employee '{employee_id}'. Status: {status}")
        return False

def _run_event_creation_test_cases(c, base_url, auth_key, employee_id, env_prefix=""):
    """イベント作成テストケース群を実行"""
    print(f"\n--- Running Event Creation Tests for {env_prefix} Environment ({base_url}) ---")
    # イベント作成テストの前に従業員が存在することを保証
    if not _ensure_test_employee_exists(c, employee_id, base_url, auth_key):
        print(f"Prerequisite: Failed to ensure employee '{employee_id}' for {env_prefix} event tests. Aborting.")
        return False 

    endpoint = f"/employees/{employee_id}/events"
    all_passed = True

    # Case 1: 必須項目のみ
    case_name_1 = f"[{env_prefix} Case 1: Required fields]"
    print(f"\n{case_name_1}")
    payload1 = {"event_type": f"Task {env_prefix}".strip(), "description": f"Reported progress. {env_prefix}".strip()}
    resp1 = _send_post_request(base_url, endpoint, json.dumps(payload1), auth_key)
    
    if not (resp1 and resp1.status_code == 201):
        print(f"{case_name_1} FAILED: Expected 201, got {resp1.status_code if resp1 else 'N/A'}")
        all_passed = False
    else:
        try:
            data1 = resp1.json()
            assert "event_id" in data1 and data1.get("employee_id") == employee_id
            print(f"{case_name_1} PASSED. Event ID: {data1.get('event_id', 'N/A')}")
        except Exception as e:
            print(f"{case_name_1} FAILED validation: {e}")
            all_passed = False

    # Case 2: timestamp と details を含む
    case_name_2 = f"[{env_prefix} Case 2: With timestamp and details]"
    print(f"\n{case_name_2}")
    payload2 = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": f"Training {env_prefix}".strip(),
        "description": f"Completed new framework training. {env_prefix}".strip(),
        "details": {"framework": f"FrameworkZ {env_prefix}".strip(), "completed": True}
    }
    resp2 = _send_post_request(base_url, endpoint, json.dumps(payload2), auth_key)

    if not (resp2 and resp2.status_code == 201):
        print(f"{case_name_2} FAILED: Expected 201, got {resp2.status_code if resp2 else 'N/A'}")
        all_passed = False
    else:
        try:
            data2 = resp2.json()
            assert "event_id" in data2 and data2.get("details", {}).get("framework") == payload2["details"]["framework"]
            print(f"{case_name_2} PASSED. Event ID: {data2.get('event_id', 'N/A')}")
        except Exception as e:
            print(f"{case_name_2} FAILED validation: {e}")
            all_passed = False
            
    result_msg = 'PASSED' if all_passed else 'COMPLETED WITH FAILURES'
    print(f"\n--- Event Creation Tests for {env_prefix} Environment: {result_msg} ---")
    return all_passed

# --- Invoke Tasks ---

@task
def setup(c):
    """Installs dependencies from requirements.txt."""
    print("Installing dependencies...")
    c.run('pip install -r requirements.txt', hide=False)
    print("Setup complete.")

@task
def run_server(c):
    """Starts the Flask development server."""
    port = API_BASE_URL.split(':')[-1] if ':' in API_BASE_URL else '5000'
    print(f"Starting Flask server on http://0.0.0.0:{port}...")
    env_vars = os.environ.copy()
    env_vars.update({'FLASK_APP': 'app.py', 'FLASK_ENV': 'development', 
                     'SECRET_AUTH_KEY': str(SECRET_AUTH_KEY) if SECRET_AUTH_KEY else ''})
    c.run(f'flask run --host=0.0.0.0 --port={port}', env=env_vars, pty=True)

@task
def test_employee_creation_local(c): # 以前の test_data_auth_local から変更
    """Directly attempts to create/overwrite a test employee (LOCAL)."""
    print(f"\n--- Test Employee Creation/Overwrite (LOCAL: {API_BASE_URL}) ---")
    
    if not SECRET_AUTH_KEY:
        print("Error: SECRET_AUTH_KEY not set. Aborting test.")
        return

    employee_id_to_create = TEST_EMPLOYEE_ID 
    endpoint = f"/employees/{employee_id_to_create}"
    # このテスト専用のペイロードを定義
    employee_payload_dict = {
        "name": f"Direct Create User {employee_id_to_create}",
        "email": f"{employee_id_to_create.replace('_', '.').lower()}@loc.example.com", # よりユニークなメール
        "role": "Direct Create Test",
        "delete_flag": False
    }
    employee_payload_str = json.dumps(employee_payload_dict)

    print(f"Attempting to POST employee data for ID: {employee_id_to_create} with payload: {employee_payload_str}")
    response = _send_post_request(API_BASE_URL, endpoint, employee_payload_str, SECRET_AUTH_KEY)

    if response and (response.status_code == 201 or response.status_code == 409):
        print(f"Employee creation/overwrite attempt for ID '{employee_id_to_create}' SUCCEEDED with status {response.status_code}.")
        try:
            print(f"Response body: {response.json()}")
        except requests.exceptions.JSONDecodeError:
            print(f"Response body (text): {response.text}")
        print("test-employee-creation-local PASSED.")
    else:
        status = response.status_code if response else "N/A"
        body = response.text if response and hasattr(response, 'text') else "No response object"
        print(f"Employee creation/overwrite attempt for ID '{employee_id_to_create}' FAILED. Status: {status}")
        print(f"Response body: {body}")
        print("test-employee-creation-local FAILED.")

@task
def test_employee_creation_prod(c): # 以前の test_data_auth_prod から変更
    """Directly attempts to create/overwrite a test employee (PROD)."""
    print(f"\n--- Test Employee Creation/Overwrite (PROD: {PROD_API_BASE_URL}) ---")

    if not PROD_API_BASE_URL:
        print("Error: PROD_API_BASE_URL is not set. Aborting test.")
        return
    
    prod_auth_key = os.getenv('PROD_SECRET_AUTH_KEY', SECRET_AUTH_KEY)
    if not prod_auth_key:
        print("Error: Auth key for PROD not set. Aborting test.")
        return

    employee_id_to_create = TEST_EMPLOYEE_ID
    endpoint = f"/employees/{employee_id_to_create}"
    employee_payload_dict = {
        "name": f"Direct Create User {employee_id_to_create} (Prod)",
        "email": f"{employee_id_to_create.replace('_', '.').lower()}@prod.example.com",
        "role": "Direct Create Test (Prod)",
        "delete_flag": False
    }
    employee_payload_str = json.dumps(employee_payload_dict)

    print(f"Attempting to POST employee data for ID: {employee_id_to_create} with payload: {employee_payload_str}")
    response = _send_post_request(PROD_API_BASE_URL, endpoint, employee_payload_str, prod_auth_key)

    if response and (response.status_code == 201 or response.status_code == 409):
        print(f"Employee creation/overwrite attempt for ID '{employee_id_to_create}' SUCCEEDED with status {response.status_code}.")
        try:
            print(f"Response body: {response.json()}")
        except requests.exceptions.JSONDecodeError:
            print(f"Response body (text): {response.text}")
        print("test-employee-creation-prod PASSED.")
    else:
        status = response.status_code if response else "N/A"
        body = response.text if response and hasattr(response, 'text') else "No response object"
        print(f"Employee creation/overwrite attempt for ID '{employee_id_to_create}' FAILED. Status: {status}")
        print(f"Response body: {body}")
        print("test-employee-creation-prod FAILED.")


@task
def test_employee_event_local(c):
    """Runs employee event creation test suite for LOCAL."""
    print(f"\n--- Starting LOCAL Employee Event Test Suite ---")
    if not SECRET_AUTH_KEY: print("Error: SECRET_AUTH_KEY not set."); return
    # イベントテストの前に、このテスト専用の従業員を作成・確認する
    # または、test_employee_creation_local に依存させる (pre=[test_employee_creation_local] のように)
    # ここでは _ensure_test_employee_exists を引き続き使用するが、
    # もし ensure が不要なら、この呼び出しを削除し、TEST_EMPLOYEE_ID が存在することを前提とするか、
    # 直前に test_employee_creation_local を手動実行する運用にする。
    # 今回は、イベントテストの前提として ensure を残します。
    _run_event_creation_test_cases(c, API_BASE_URL, SECRET_AUTH_KEY, TEST_EMPLOYEE_ID, "LOCAL")

@task
def test_employee_event_prod(c):
    """Runs employee event creation test suite for PROD."""
    print(f"\n--- Starting PROD Employee Event Test Suite ---")
    if not PROD_API_BASE_URL: print("Error: PROD_API_BASE_URL not set."); return
    auth_key = os.getenv('PROD_SECRET_AUTH_KEY', SECRET_AUTH_KEY)
    if not auth_key: print("Error: Auth key for PROD not set."); return
    _run_event_creation_test_cases(c, PROD_API_BASE_URL, auth_key, TEST_EMPLOYEE_ID, "PROD")

# 旧 test_data_auth_local と test_data_auth_prod は削除しました。
# 必要であれば、シンプルな /data エンドポイントの疎通確認タスクとして別途作成も可能です。

# To see available tasks: invoke --list
# To run a task: invoke <task-name> (e.g., invoke setup, invoke test-employee-creation-local)