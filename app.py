# -*- coding: utf-8 -*-
"""
基本的なFlaskアプリケーション
- GET / : "Hello World" を返す
- POST /data : ヘッダーに正しい認証キーがあれば成功メッセージを返す
"""

from flask import Flask, request, jsonify
import os # 環境変数からキーを読み込むために追加

# Flaskアプリケーションのインスタンスを作成
app = Flask(__name__)

# --- 認証キーの設定 ---
# 本来は環境変数や設定ファイルから読み込むべきですが、
# ここでは仮のキーを定義します。
# 環境変数 'SECRET_AUTH_KEY' が設定されていればそれを使用し、
# なければデフォルトの 'mysecretkey' を使用します。
SECRET_KEY = os.environ.get('SECRET_AUTH_KEY', 'mysecretkey')

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
    if auth_key and auth_key == SECRET_KEY:
        # キーが正しい場合
        # ここで実際にPOSTされたデータを処理するロジックを追加できます
        # 例: post_data = request.get_json()
        #     print(f"Received data: {post_data}")
        return jsonify({"message": "Data received successfully"}), 200 # 成功レスポンス (ステータスコード 200 OK)
    else:
        # キーがない、または間違っている場合
        return jsonify({"error": "Unauthorized"}), 401 # エラーレスポンス (ステータスコード 401 Unauthorized)

if __name__ == '__main__':
    # デバッグモードを有効にして実行 (開発時のみ推奨)
    # ポート番号はデフォルトの5000
    app.run(debug=True, host='0.0.0.0')

