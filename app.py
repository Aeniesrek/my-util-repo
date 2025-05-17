# -*- coding: utf-8 -*-
"""
基本的なFlaskアプリケーション
- GET / : "Hello World" を返す
- POST /data : ヘッダーに正しい認証キーがあれば成功メッセージを返す
"""

import os
from flask import Flask, request, jsonify
from google.cloud import datastore
from dotenv import load_dotenv
from datetime import datetime, timezone # 追加
import json # 追加

load_dotenv()
app = Flask(__name__)

# Datastoreクライアントの初期化
try:
    # GOOGLE_APPLICATION_CREDENTIALS は引き続き使われます
    # プロジェクトIDはサービスアカウントキーから自動で読み取られるか、
    # 明示的に datastore.Client(project='moriguchiapplication') とすることも可能です。
    # 通常は自動で認識されます。
    db = datastore.Client()
    print("Datastore client initialized successfully.")
except Exception as e:
    print(f"Error initializing Datastore client: {e}")
    db = None

# --- 認証キーの設定 ---
# 本来は環境変数や設定ファイルから読み込むべきですが、
# ここでは仮のキーを定義します。
# 環境変数 'SECRET_AUTH_KEY' が設定されていればそれを使用し、
# なければデフォルトの 'mysecretkey' を使用します。
SECRET_AUTH_KEY = os.environ.get('SECRET_AUTH_KEY', 'mysecretkey_app_default') # デフォルト値も変更推奨

@app.route('/')
def hello_world():
    """
    ルートURL ('/') へのGETリクエストに応答する関数
    """
    return jsonify({"message": "Hello World"})

@app.route('/data', methods=['POST'])
def handle_post_data():
    """
    '/data' エンドポイントへのPOSTリクエストを処理する関数
    ヘッダー 'X-Auth-Key' による簡単な認証を行う
    """
    # リクエストヘッダーから 'X-Auth-Key' の値を取得
    auth_key = request.headers.get('X-Auth-Key')

    # 認証キーの検証
    if auth_key and auth_key == SECRET_AUTH_KEY:
        # キーが正しい場合
        # ここで実際にPOSTされたデータを処理するロジックを追加できます
        # 例: post_data = request.get_json()
        #     print(f"Received data: {post_data}")
        return jsonify({"message": "Data received successfully"}), 200 # 成功レスポンス (ステータスコード 200 OK)
    else:
        # キーがない、または間違っている場合
        return jsonify({"error": "Unauthorized"}), 401 # エラーレスポンス (ステータスコード 401 Unauthorized)

@app.route('/employees/<string:employee_id>', methods=['POST'])
def create_employee(employee_id):

    if not db:
        return jsonify({"error": "Datastore client not initialized"}), 500
    try:
        employee_data = request.get_json()

        # リクエストボディからJSONデータを取得
        # もしリクエストボディが空であれば、400 Bad Requestを返す
        if not employee_data:
            return jsonify({"error": "Missing data"}), 400

        kind = 'employees'  # DatastoreのKind名
        # employee_id をキーのnameとして使用
        key = db.key(kind, employee_id)

        # Datastoreではエンティティが既に存在するかどうかを確認するにはget()を使います。
        # get()でNoneが返ってこなければ存在すると判断できます。
        entity = db.get(key)
        if entity:
            return jsonify({"error": f"Employee with ID {employee_id} already exists"}), 409

        # 新しいエンティティを作成
        entity = datastore.Entity(key=key)
        # リクエストデータからエンティティのプロパティを設定
        # (delete_flagなど、Firestoreの時と同様のロジック)
        entity.update({
            "name": employee_data.get("name"),
            "email": employee_data.get("email"),
            "role": employee_data.get("role"),
            "delete_flag": employee_data.get("delete_flag", False)
        })

        # 必須フィールドのチェック
        if not entity.get("name") or not entity.get("email"):
            return jsonify({"error": "Missing required fields: name and email"}), 400

        db.put(entity) # エンティティを保存 (Firestoreのset()に相当)
        # レスポンス用にエンティティのプロパティとIDを返す
        response_data = dict(entity) # エンティティのプロパティを辞書に変換
        response_data['id'] = employee_id # IDも追加しておく

        return jsonify({"message": f"Employee {employee_id} created successfully", "data": response_data}), 201

    except Exception as e:
        app.logger.error(f"Error creating employee {employee_id}: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@app.route('/employees/<string:employee_id>', methods=['GET'])
def get_employee(employee_id):
    if not db:
        return jsonify({"error": "Datastore client not initialized"}), 500
    try:
        kind = 'employees'
        key = db.key(kind, employee_id)
        entity = db.get(key) # キーでエンティティを取得 (Firestoreのdoc.get()に相当)

        if entity:
            # エンティティのプロパティを辞書として返す
            return jsonify(dict(entity)), 200
        else:
            return jsonify({"error": "Employee not found"}), 404

    except Exception as e:
        app.logger.error(f"Error getting employee {employee_id}: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500

def authenticate(current_request):
    """リクエストヘッダーのX-Auth-Keyを検証する"""
    # SECRET_AUTH_KEY は Flask アプリケーションのどこかで .env から読み込まれている想定
    # 例: app = Flask(__name__); app.config['SECRET_AUTH_KEY'] = os.getenv('SECRET_AUTH_KEY')
    # または、このファイルのトップレベルで SECRET_AUTH_KEY = os.getenv('SECRET_AUTH_KEY') と定義
    
    # ここでは、ファイルスコープまたはアプリケーション設定から SECRET_AUTH_KEY を取得すると仮定
    # tasks.py と同様にファイル冒頭で定義されている SECRET_AUTH_KEY を使う場合:
    # (tasks.py と同じように SECRET_AUTH_KEY = os.getenv('SECRET_AUTH_KEY', 'デフォルト値') が app.py にあるか確認)

    auth_key_header = current_request.headers.get('X-Auth-Key')
    
    # SECRET_AUTH_KEY がグローバル変数として定義されているか、
    # または app.config などから取得する必要がある
    # ここでは仮に `app.secret_key` や `app.config['SECRET_AUTH_KEY']` を使うか、
    # このファイルのグローバルスコープで定義された SECRET_AUTH_KEY を使うとします。
    # 今回は、ファイル上部で os.getenv で取得した SECRET_AUTH_KEY 変数があると仮定します。
    # (例: SECRET_AUTH_KEY = os.getenv('SECRET_AUTH_KEY'))

    if auth_key_header and auth_key_header == SECRET_AUTH_KEY: # SECRET_AUTH_KEY は app.py 内で定義されている想定
        return True
    return False

@app.route('/employees/<employee_id>/events', methods=['POST'])
def create_employee_event(employee_id):
    """
    指定された従業員IDに新しい出来事イベントを追加します。
    """
    if not authenticate(request):
        return jsonify({"error": "Unauthorized"}), 401

    client = datastore.Client()

    # 1. 従業員の存在確認
    employee_key = client.key('employees', employee_id)
    employee = client.get(employee_key)
    if not employee:
        return jsonify({"error": f"Employee with ID {employee_id} not found"}), 404

    # 2. リクエストボディの取得とバリデーション
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON payload"}), 400
    except Exception:
        return jsonify({"error": "Invalid JSON payload"}), 400

    event_type = data.get('event_type')
    description = data.get('description')

    if not event_type or not isinstance(event_type, str):
        return jsonify({"error": "Missing or invalid 'event_type' (string)"}), 400
    if not description or not isinstance(description, str):
        return jsonify({"error": "Missing or invalid 'description' (string)"}), 400

    # 3. timestamp の処理 (ISO 8601形式を期待、なければ現在時刻UTC)
    try:
        request_timestamp_str = data.get('timestamp')
        if request_timestamp_str:
            # タイムゾーン情報があればそれを尊重し、なければUTCとみなす（あるいはエラー）
            # fromisoformatはPython 3.7+
            event_timestamp = datetime.fromisoformat(request_timestamp_str)
            # DatastoreにはUTCで保存するのが推奨
            if event_timestamp.tzinfo is None: # タイムゾーン情報がない場合、UTCと解釈
                 event_timestamp = event_timestamp.replace(tzinfo=timezone.utc)
            else:
                 event_timestamp = event_timestamp.astimezone(timezone.utc)
        else:
            event_timestamp = datetime.now(timezone.utc)
    except ValueError:
        return jsonify({"error": "Invalid 'timestamp' format. Use ISO 8601 format."}), 400


    # 4. details の処理 (dictであればJSON文字列に変換)
    details_dict = data.get('details')
    details_str = None
    if details_dict is not None:
        if not isinstance(details_dict, dict):
            return jsonify({"error": "'details' must be a JSON object (dict)"}), 400
        try:
            details_str = json.dumps(details_dict)
        except TypeError:
            return jsonify({"error": "Failed to serialize 'details' to JSON string"}), 400


    # 5. created_at, updated_at の設定
    now_utc = datetime.now(timezone.utc)
    created_at = now_utc
    updated_at = now_utc

    # 6. Datastoreエンティティの作成と保存
    try:
        # 親キー (従業員) を指定
        parent_key = client.key('employees', employee_id)
        # EmployeeEventエンティティのキー (IDは自動生成)
        event_key = client.key('employee_event', parent=parent_key)
        
        event_entity = datastore.Entity(key=event_key)
        event_entity.update({
            'timestamp': event_timestamp,
            'event_type': event_type,
            'description': description,
            # 'details': details_str, # details_strがNoneの場合もそのまま保存
            'created_at': created_at,
            'updated_at': updated_at
        })
        # details_strがNoneでない場合のみセットする
        if details_str is not None:
            event_entity['details'] = details_str

        client.put(event_entity)
        
        # 自動生成されたIDを取得
        generated_event_id = str(event_entity.key.id) # IDは数値なので文字列に変換

        # 7. レスポンスデータの構築
        response_data = {
            "event_id": generated_event_id,
            "employee_id": employee_id,
            "timestamp": event_timestamp.isoformat(),
            "event_type": event_type,
            "description": description,
            "details": details_dict, # レスポンスでは元のdict形式で返す (Noneの場合もある)
            "created_at": created_at.isoformat(),
            "updated_at": updated_at.isoformat()
        }
        return jsonify(response_data), 201

    except Exception as e:
        print(f"Error creating employee event: {e}") # サーバーログ用
        return jsonify({"error": "Internal Server Error"}), 500
        
if __name__ == '__main__':
    # デバッグモードを有効にして実行 (開発時のみ推奨)
    # ポート番号はデフォルトの5000
    app.run(debug=True, host='0.0.0.0')

