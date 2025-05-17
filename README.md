このプロジェクトは、Python (Flask) を使用して構築された Web API アプリケーションです。Google Cloud Platform (GCP) 上の Cloud Run にデプロイされ、データストレージとして Cloud Datastore (Firestore in Datastore mode) を利用します。

## 概要

主な機能として、従業員情報および従業員ごとのイベント情報を管理するための API エンドポイントを提供します。認証にはリクエストヘッダーの `X-Auth-Key` を使用します。

## 技術スタック

- **バックエンド:** Python, Flask
- **データベース:** Google Cloud Datastore (Firestore in Datastore mode)
- **デプロイメント:** Google Cloud Run, Docker, Gunicorn
- **CI/CD:** Google Cloud Build, Artifact Registry
- **認証キー管理:** Google Secret Manager
- **タスクランナー:** Invoke
- **主要ライブラリ:** `google-cloud-datastore`, `requests`, `python-dotenv`

## ローカル開発環境セットアップ

### 前提条件

- Python 3.10+
- Git
- WSL (Windows Subsystem for Linux) または Linux/macOS 環境
- Google Cloud SDK (gcloud CLI) - Datastore エミュレータや GCP 操作に必要に応じて

### 手順

1.  **リポジトリをクローン:**

    ```bash
    git clone [https://github.com/Aeniesrek/my-util-repo.git](https://github.com/Aeniesrek/my-util-repo.git)
    cd my-util-repo
    ```

2.  **Python 仮想環境の作成とアクティベート:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **依存関係のインストール:**
    `invoke` を使ってインストールします。

    ```bash
    invoke setup
    ```

    または、直接 `pip` を使用します。

    ```bash
    pip install -r requirements.txt
    ```

4.  **`.env` ファイルの作成と設定:**
    プロジェクトルートにある `.env.example` ファイルをコピーして `.env` ファイルを作成し、以下の環境変数を設定してください。

    ```dotenv
    # .env ファイルの例
    API_BASE_URL=[http://127.0.0.1:5000](http://127.0.0.1:5000)
    SECRET_AUTH_KEY=your_strong_secret_auth_key_for_local_development
    GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json

    # 本番環境テスト用 (任意)
    PROD_API_BASE_URL=[https://your-cloud-run-service-url.a.run.app](https://your-cloud-run-service-url.a.run.app)
    # PROD_SECRET_AUTH_KEY=your_actual_production_secret_key (設定しない場合はSECRET_AUTH_KEYが使われます)

    # tasks.pyのテスト用データ (任意)
    TEST_ITEM_DATA={"message": "Test message for /data endpoint"}
    ```

    - `API_BASE_URL`: ローカル開発サーバーの URL。
    - `SECRET_AUTH_KEY`: API 認証に使用するキー（ローカル開発用）。
    - `GOOGLE_APPLICATION_CREDENTIALS`: ローカルから GCP の Datastore に接続するためのサービスアカウントキー JSON ファイルへの絶対パス。
    - `PROD_API_BASE_URL`: デプロイされた Cloud Run サービスの URL（本番環境テスト用）。
    - `PROD_SECRET_AUTH_KEY`: (任意) 本番環境テスト用の認証キー。未設定の場合、`tasks.py` は `SECRET_AUTH_KEY` をフォールバックとして使用します。
    - `TEST_ITEM_DATA`: `tasks.py` の `/data` エンドポイントテストで使用する JSON 文字列。

## ローカルでの実行方法

1.  **開発サーバーの起動:**
    別のターミナルで以下のコマンドを実行し、Flask 開発サーバーを起動します。

    ```bash
    invoke run-server
    ```

    サーバーはデフォルトで `http://127.0.0.1:5000` で起動します。

2.  **API のテスト (ローカル):**
    別のターミナルで以下の `invoke` タスクを実行して、ローカルサーバーに対して API テストを行います。
    - 従業員作成 API のテスト:
      ```bash
      invoke test-employee-creation-local
      ```
    - 従業員イベント作成 API のテスト:
      `bash
    invoke test-employee-event-local
    `
      これらのテストは、Datastore にテストデータ（従業員 ID: `test_emp_001`）を作成します。

## API エンドポイント (主要なもの)

ベース URL: `http://127.0.0.1:5000` (ローカル) または Cloud Run の URL (本番)
認証: 全てのエンドポイント（`/` を除く）でリクエストヘッダーに `X-Auth-Key: <SECRET_AUTH_KEYの値>` が必要です。

- **`GET /`**

  - 説明: Hello World メッセージを返します。
  - 認証: 不要

- **`POST /data`**

  - 説明: 認証テスト用のエンドポイント。成功するとメッセージを返します。
  - 認証: 必要
  - リクエストボディ (例): `{"message": "test"}` (Content-Type: application/json)

- **`POST /employees/<employee_id>`**

  - 説明: 新しい従業員を作成します。
  - 認証: 必要
  - パスパラメータ: `employee_id` (文字列, 従業員の一意な ID)
  - リクエストボディ (JSON):
    ```json
    {
      "name": "Taro Yamada",
      "email": "taro.yamada@example.com",
      "role": "Developer",
      "delete_flag": false
    }
    ```
  - 成功レスポンス (201): 作成された従業員データ。
  - エラーレスポンス: 400 (不正なリクエスト), 409 (既に存在する場合)。

- **`GET /employees/<employee_id>`**

  - 説明: 指定された ID の従業員情報を取得します。
  - 認証: 必要
  - パスパラメータ: `employee_id`
  - 成功レスポンス (200): 従業員データ。
  - エラーレスポンス: 404 (見つからない場合)。

- **`POST /employees/<employee_id>/events`**
  - 説明: 指定された従業員に新しいイベントを作成します。
  - 認証: 必要
  - パスパラメータ: `employee_id` (親となる従業員の ID)
  - リクエストボディ (JSON):
    ```json
    {
      "event_type": "Project Meeting",
      "description": "Discussed project milestones.",
      "timestamp": "2025-05-18T10:00:00Z", // (オプション) ISO 8601形式。省略時は現在時刻。
      "details": {
        // (オプション) フリーフォーマットなJSONオブジェクト
        "project_name": "Alpha Project",
        "attendees": ["Alice", "Bob"]
      }
    }
    ```
  - 成功レスポンス (201): 作成されたイベントデータ。
  - エラーレスポンス: 400 (不正なリクエスト), 404 (親従業員が見つからない場合)。

## デプロイメント

このアプリケーションは、`main` ブランチへのプッシュをトリガーとして、Google Cloud Build を使用して自動的にビルドされ、Artifact Registry を経由して Google Cloud Run にデプロイされます。

- **リージョン:** `asia-northeast2`
- **Cloud Run サービス名:** `hello-world-api-service` (設定による)
- **認証キー (`SECRET_AUTH_KEY`):** Cloud Run 環境では、Secret Manager に `api-auth-key` という名前で保存されたシークレットの最新バージョンから環境変数として設定されます。

## `tasks.py` (Invoke タスク一覧)

`invoke --list` コマンドで利用可能なタスクの一覧と説明を確認できます。主要なタスクは以下の通りです。

- `setup`: 依存関係 (`requirements.txt`) をインストールします。
- `run-server`: ローカルで Flask 開発サーバーを起動します (アプリケーションファクトリ `app:create_app()` を使用)。
- `test-employee-creation-local`: ローカル環境に対して従業員作成 API のテストを実行します。
- `test-employee-creation-prod`: 本番環境 (Cloud Run) に対して従業員作成 API のテストを実行します (`.env` の `PROD_API_BASE_URL` を使用)。
- `test-employee-event-local`: ローカル環境に対して従業員イベント作成 API のテストを実行します。
- `test-employee-event-prod`: 本番環境に対して従業員イベント作成 API のテストを実行します。

## フォルダ構成 (概要)
