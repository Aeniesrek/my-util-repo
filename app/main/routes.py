# app/main/routes.py

from flask import jsonify, request, current_app
# 認証デコレータを app/auth.py からインポート
from app.auth import authenticate_request 
# main_bp は app/main/__init__.py で定義されていると仮定し、そこからインポート
from . import main_bp 


@main_bp.route('/')
def hello_world():
    """
    Hello World エンドポイント。
    """
    return jsonify({"message": "Hello World"})

@main_bp.route('/data', methods=['POST'])
@authenticate_request # authenticate_request デコレータを適用
def handle_post_data():
    """
    認証付きデータ受信エンドポイント。
    リクエストヘッダーの 'X-Auth-Key' で認証を行います。
    """
    # dbクライアントへのアクセス例 (このエンドポイントでは現在使用していません)
    # db = current_app.db
    # if not db:
    #     return jsonify({"error": "Datastore client not initialized"}), 500
            
    # authenticate_request デコレータが認証処理を行うため、ここでは認証ロジックは不要
    return jsonify({"message": "Data received successfully (Authenticated)"}), 200

