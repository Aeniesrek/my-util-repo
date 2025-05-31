# app/__init__.py

import os
from flask import Flask
from google.cloud import datastore
from dotenv import load_dotenv
import google.generativeai as genai

# .envファイルの読み込みをここで行う
load_dotenv() 

def create_app(config_name=None):
    print("--- create_app() CALLED ---") # 既存のprint
    app_instance = Flask(__name__)

    # --- 設定の読み込み ---
    app_instance.config['SECRET_AUTH_KEY'] = os.environ.get('SECRET_AUTH_KEY', 'mysecretkey_app_init_default')
    
    # GOOGLE_GEN_AI_API_KEY の取得状況を詳細にログ出力
    retrieved_gen_ai_key = os.environ.get('GOOGLE_GEN_AI_API_KEY')
    print(f"DEBUG: Value from os.environ.get('GOOGLE_GEN_AI_API_KEY'): '{retrieved_gen_ai_key}' (type: {type(retrieved_gen_ai_key)})")
    
    if retrieved_gen_ai_key is not None:
        app_instance.config['GOOGLE_GEN_AI_API_KEY'] = retrieved_gen_ai_key
        print(f"DEBUG: Set app_instance.config['GOOGLE_GEN_AI_API_KEY'] to: '{retrieved_gen_ai_key}'")
    else:
        print("DEBUG: GOOGLE_GEN_AI_API_KEY was NOT found in os.environ.")
        # KeyErrorを避けるため、キーが存在しない場合は明示的に設定しないか、
        # あるいはデフォルト値を設定するなどの対応も考えられます。
        # ここでは、キーが存在しない場合はconfigに設定しないようにしてみます。

    # ... (SECRET_AUTH_KEY のチェック) ...

    # --- Datastoreクライアントの初期化 ---
    try:
        project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
        if project_id:
            app_instance.db = datastore.Client(project=project_id)
        else:
            app_instance.db = datastore.Client()
        print("Datastore client initialized and attached to app instance.") # 既存のprint
    except Exception as e:
        print(f"Error initializing Datastore client in create_app: {e}")
        app_instance.db = None

    # --- Google Generative AI クライアントの初期化 ---
    # configオブジェクトの現在のキー一覧をログ出力
    print(f"DEBUG: Keys currently in app_instance.config: {list(app_instance.config.keys())}")
    
    # より安全なキーの存在確認と値の評価
    if 'GOOGLE_GEN_AI_API_KEY' in app_instance.config and app_instance.config.get('GOOGLE_GEN_AI_API_KEY'):
        api_key_to_use = app_instance.config['GOOGLE_GEN_AI_API_KEY']
        print(f"DEBUG: Found GOOGLE_GEN_AI_API_KEY in config. Value: '{api_key_to_use}'. Proceeding with genai.configure.")
        try:
            # !!! 重要: エンドポイントの指定がまだ必要です !!!
            # google-generativeai==0.8.5 での正しいエンドポイント指定方法を再度ご確認ください。
            # 例: client_options={"api_endpoint": "us-central1-aiplatform.googleapis.com"}
            genai.configure(
                api_key=api_key_to_use
                # , client_options={"api_endpoint": "us-central1-aiplatform.googleapis.com"} # <-- このような指定が必要
            )
            print("Google Generative AI configured.") # 既存のprint
        except Exception as e:
            print(f"Error configuring Google Generative AI: {e}")
            app_instance.logger.warning(f"Failed to configure Google Generative AI: {e}. Generative AI features may not work.")
    else:
        missing_reason = ""
        if 'GOOGLE_GEN_AI_API_KEY' not in app_instance.config:
            missing_reason = "key not found in config"
        elif not app_instance.config.get('GOOGLE_GEN_AI_API_KEY'):
            missing_reason = "key is in config but value is None or empty"
        
        print(f"DEBUG: GOOGLE_GEN_AI_API_KEY {missing_reason}. Generative AI features may not work.")
        app_instance.logger.warning(f"GOOGLE_GEN_AI_API_KEY {missing_reason}. Generative AI features may not work.")
    
    # --- Blueprintの登録 ---
    from .main import main_bp
    # 'main_bp_instance' のような、アプリケーション内でユニークな名前を明示的に指定
    app_instance.register_blueprint(main_bp, name=f"main_bp_instance_{os.getpid()}") # プロセスIDなどでさらにユニークに

    from .employees import employees_bp
    app_instance.register_blueprint(employees_bp, name=f"employees_bp_instance_{os.getpid()}")

    from .meeting_summary import bp as meeting_summary_bp
    app_instance.register_blueprint(meeting_summary_bp, url_prefix='/meeting-summary')
    
    from .google_meet_maps.routes import google_meet_map_bp

    app_instance.register_blueprint(google_meet_map_bp)


    return app_instance