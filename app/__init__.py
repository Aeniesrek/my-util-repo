# app/__init__.py

import os
from flask import Flask
from google.cloud import datastore
from dotenv import load_dotenv
import google.generativeai as genai

# .envファイルの読み込みをここで行う
load_dotenv() 

def create_app(config_name=None):
    app_instance = Flask(__name__)

    # --- 設定の読み込み ---
    app_instance.config['SECRET_AUTH_KEY'] = os.environ.get('SECRET_AUTH_KEY', 'mysecretkey_app_init_default')
    app_instance.config['GOOGLE_GEN_AI_API_KEY'] = os.environ.get('GOOGLE_GEN_AI_API_KEY')

    # ... (SECRET_AUTH_KEY のチェック) ...

    # --- Datastoreクライアントの初期化 ---
    try:
        # プロジェクトIDを環境変数から取得するように変更 (Cloud Run デプロイ時を想定)
        project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
        if project_id:
            app_instance.db = datastore.Client(project=project_id)
        else:
            # ローカル開発などでプロジェクトIDが設定されていない場合のフォールバック
            app_instance.db = datastore.Client() # ローカルエミュレータまたはデフォルトプロジェクトに接続
        print("Datastore client initialized and attached to app instance.")
    except Exception as e:
        print(f"Error initializing Datastore client in create_app: {e}")
        app_instance.db = None

    # --- Google Generative AI クライアントの初期化 ---
    if app_instance.config['GOOGLE_GEN_AI_API_KEY']:
        try:
            genai.configure(api_key=app_instance.config['GOOGLE_GEN_AI_API_KEY'])
            print("Google Generative AI configured.")
        except Exception as e:
            print(f"Error configuring Google Generative AI: {e}")
            app_instance.logger.warning(f"Failed to configure Google Generative AI: {e}. Generative AI features may not work.")
    else:
        print("GOOGLE_GEN_AI_API_KEY is not set. Generative AI features may not work.")
        app_instance.logger.warning("GOOGLE_GEN_AI_API_KEY is not set. Generative AI features may not work.")

    
    # --- Blueprintの登録 ---
    from .main import main_bp
    # 'main_bp_instance' のような、アプリケーション内でユニークな名前を明示的に指定
    app_instance.register_blueprint(main_bp, name=f"main_bp_instance_{os.getpid()}") # プロセスIDなどでさらにユニークに

    from .employees import employees_bp
    app_instance.register_blueprint(employees_bp, name=f"employees_bp_instance_{os.getpid()}")

    from .meeting_summary import bp as meeting_summary_bp
    app_instance.register_blueprint(meeting_summary_bp, url_prefix='/meeting-summary')


    return app_instance