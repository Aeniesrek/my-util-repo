# ベースとなる公式Pythonイメージを指定します。
# python:3.12-slim は比較的小さなイメージです。バージョンは適宜変更可能です。
FROM python:3.12-slim

# コンテナ内の作業ディレクトリを設定します。これ以降の命令はこのディレクトリ基準で実行されます。
WORKDIR /app

# まず依存関係ファイルだけをコピーし、pip installを実行します。
# こうすることで、コード(app.py)だけを変更した場合、依存関係のインストール手順はキャッシュが利用され、ビルドが速くなります。
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードなど、カレントディレクトリの残りのファイルをコンテナの作業ディレクトリにコピーします。
# ( .dockerignore ファイルで不要なファイルは除外するのが望ましいです )
# アプリケーションファクトリパターンでは、appフォルダ全体をコピーする必要があります。
COPY app ./app 
COPY run.py .
# COPY . . # <-- 以前のままでも良いが、上記のように具体的に指定する方が明確

# Cloud Run は PORT 環境変数でリッスンすべきポートを指定します。
# EXPOSE 命令は主にドキュメント目的ですが、デフォルトのポートを記述しておきます。
EXPOSE ${PORT:-8080}

# コンテナが起動したときに実行されるコマンドを指定します。
CMD gunicorn --bind "0.0.0.0:$PORT" --workers 1 --log-level debug "app:create_app()"