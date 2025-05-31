# app/google_meet_maps/routes.py
from flask import request, jsonify # Blueprintもこちらでインポート
from google.cloud import datastore
import logging
from flask import Blueprint # routes.pyでBlueprintを定義する場合

# from app.auth import authenticate_request # 必要に応じて

google_meet_map_bp = Blueprint('google_meet_map', __name__, url_prefix='/google_meet_employee_map')

@google_meet_map_bp.route('/<path:email>', methods=['POST'])
# @authenticate_request
def add_or_update_google_meet_mapping(email):
    # (前回の回答に記載した実装内容)
    client = datastore.Client()
    kind = "google_meet_employee_map"
    key = client.key(kind, email)

    data = request.get_json()
    if not data or 'google_meet_name' not in data:
        return jsonify({"error": "リクエストボディに 'google_meet_name' が必要です"}), 400

    google_meet_name = data.get('google_meet_name')
    if not isinstance(google_meet_name, str) or not google_meet_name.strip():
        return jsonify({"error": "'google_meet_name' は空でない文字列である必要があります"}), 400

    entity = datastore.Entity(key=key)
    entity.update({
        "email": email,
        "google_meet_name": google_meet_name.strip()
    })

    try:
        client.put(entity)
        logging.info(f"Google Meetマッピングを保存しました: {email} -> {google_meet_name.strip()}")
        response_data = {
            "message": "Google Meetマッピングが正常に保存されました",
            "email": email,
            "google_meet_name": google_meet_name.strip()
        }
        return jsonify(response_data), 200 # または201
    except Exception as e:
        logging.error(f"Datastoreへの保存中にエラーが発生しました (email: {email}): {e}")
        return jsonify({"error": f"マッピングの保存に失敗しました: {str(e)}"}), 500