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
COPY . .

# Cloud Run は PORT 環境変数でリッスンすべきポートを指定します。
# EXPOSE 命令は主にドキュメント目的ですが、デフォルトのポートを記述しておきます。
EXPOSE ${PORT:-8080}

# コンテナが起動したときに実行されるコマンドを指定します。
# ["python", "app.py"] で、ローカルで実行したのと同じようにFlaskの開発サーバーを起動します。
# 本番環境では Gunicorn などを使うのが一般的ですが、まずはこれで動かします。
CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "1", "app:app"]