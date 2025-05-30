# app/auth.py

from flask import request, jsonify, current_app
import functools

def authenticate_request(f):
    """
    リクエストヘッダーの 'X-Auth-Key' を検証するデコレータ。
    """
    @functools.wraps(f) # これにより、デコレートされた関数の名前やドキュメントが保持されます。
    def decorated_function(*args, **kwargs):
        auth_key = request.headers.get('X-Auth-Key')
        
        if not auth_key:
            current_app.logger.error("Authorization header missing.")
            return jsonify({"message": "Authorization header missing"}), 401
        
        # current_app.config['SECRET_AUTH_KEY'] は app/__init__.py で設定されています
        # 環境変数 SECRET_AUTH_KEY の値と一致するかを検証
        if auth_key != current_app.config.get('SECRET_AUTH_KEY'):
            current_app.logger.warning(f"Unauthorized access attempt with key: {auth_key}")
            return jsonify({"message": "Unauthorized"}), 401
        
        return f(*args, **kwargs)
    return decorated_function

