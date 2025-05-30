# run.py (my-util-repo/run.py)

from app import create_app # appパッケージからcreate_app関数をインポート
import os

# アプリケーションインスタンスを作成
# 将来的に開発用、テスト用、本番用で設定を切り替える場合は、
# os.environ.get('FLASK_CONFIG') のような環境変数で config_name を渡すことができる
flask_app = create_app() 

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    # debug=True は開発時のみ。本番環境ではFalseにするか、環境変数で制御。
    flask_app.run(host='0.0.0.0', port=port, debug=True)