## ローカルでの実行方法

1.  仮想環境を有効化します:
    ```bash
    source venv/Scripts/activate
    ```
2.  (もしあれば) 必要な環境変数を設定します:
    ```bash
    export FLASK_APP=app.py
    export FLASK_ENV=development
    # export DATABASE_URL=... など
    ```
3.  Flask 開発サーバーを起動します:
    ```bash
    flask run
    ```
