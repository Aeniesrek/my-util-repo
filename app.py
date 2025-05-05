from flask import Flask, jsonify
import os

# Flaskアプリケーションのインスタンスを作成
app = Flask(__name__)

# ルートURL ('/') にアクセスがあった場合の処理
@app.route('/')
def hello_world():
    """ "Hello World" メッセージをJSON形式で返す """
    return jsonify({"message": "Hello World from GCP!"})

# スクリプトが直接実行された場合にサーバーを起動
if __name__ == "__main__":
    # Cloud Run は PORT 環境変数でポートを指定するため、それを読み込む (なければデフォルト8080)
    port = int(os.environ.get("PORT", 8080))
    # '0.0.0.0' でリッスンし、外部からのアクセスを受け付けられるようにする
    # debug=True は開発モード。エラー時にブラウザに詳細が表示される (本番ではFalse推奨)
    app.run(debug=True, host='0.0.0.0', port=port)