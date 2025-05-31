# app/employees/routes.py

from flask import jsonify, request, current_app
from google.cloud import datastore
from datetime import datetime, timezone
import json
import traceback

from . import employees_bp # 同じディレクトリの__init__.pyで定義したemployees_bpをインポート

# 認証関数をmain Blueprintからインポート (長期的には専用モジュール推奨)
# このインポートが循環参照エラーを起こさないか注意が必要です。
# もしエラーになる場合は、authenticate関数を app/auth.py のような別ファイルに移動し、
# そこから main と employees の両方でインポートするように変更します。
try:
    from app.main.routes import authenticate_request
except ImportError: 
    # 開発中の仮のフォールバック (本番では解決が必要)
    def authenticate_request(current_request):
        current_app.logger.error("CRITICAL: authenticate function could not be imported for employees_bp!")
        return False # 安全のため認証失敗とする

@employees_bp.route('/<string:employee_id>', methods=['POST'])
def create_employee(employee_id):
    db_client = current_app.db
    if not db_client:
        return jsonify({"error": "Datastore client not initialized"}), 500
    
    if not authenticate_request(request):
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        employee_data = request.get_json()
        if not employee_data:
            return jsonify({"error": "Missing data"}), 400

        kind = 'employees'
        key = db_client.key(kind, employee_id)
        entity = db_client.get(key)

        if entity:
            return jsonify({"error": f"Employee with ID {employee_id} already exists"}), 409

        entity = datastore.Entity(key=key)
        entity.update({
            "name": employee_data.get("name"),
            "email": employee_data.get("email"),
            "role": employee_data.get("role")
        })

        if not entity.get("name") or not entity.get("email"):
            return jsonify({"error": "Missing required fields: name and email"}), 400

        db_client.put(entity)
        response_data = dict(entity)
        response_data['id'] = employee_id 
        return jsonify({"message": f"Employee {employee_id} created successfully", "data": response_data}), 201
    except Exception as e:
        current_app.logger.error(f"Error creating employee {employee_id}: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@employees_bp.route('/<string:employee_id>', methods=['GET'])
def get_employee(employee_id):
    db_client = current_app.db
    if not db_client:
        return jsonify({"error": "Datastore client not initialized"}), 500

    if not authenticate_request(request):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        kind = 'employees'
        key = db_client.key(kind, employee_id)
        entity = db_client.get(key)
        if entity:
            return jsonify(dict(entity)), 200
        else:
            return jsonify({"error": "Employee not found"}), 404
    except Exception as e:
        current_app.logger.error(f"Error getting employee {employee_id}: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@employees_bp.route('/<string:employee_id>/events', methods=['POST']) # パスは /employees/<employee_id>/events となる
def create_employee_event(employee_id):
    db_client = current_app.db
    if not db_client:
        return jsonify({"error": "Datastore client not initialized"}), 500
    
    if not authenticate_request(request):
        return jsonify({"error": "Unauthorized"}), 401

    employee_key = db_client.key('employees', employee_id)
    employee = db_client.get(employee_key)
    if not employee:
        return jsonify({"error": f"Employee with ID {employee_id} not found for event creation"}), 404

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON payload for event"}), 400
    except Exception:
        return jsonify({"error": "Invalid JSON payload for event"}), 400

    event_type = data.get('event_type')
    description = data.get('description')

    if not event_type or not isinstance(event_type, str):
        return jsonify({"error": "Missing or invalid 'event_type' (string) for event"}), 400
    if not description or not isinstance(description, str):
        return jsonify({"error": "Missing or invalid 'description' (string) for event"}), 400
    
    try:
        request_timestamp_str = data.get('timestamp')
        if request_timestamp_str:
            event_timestamp = datetime.fromisoformat(request_timestamp_str)
            if event_timestamp.tzinfo is None:
                event_timestamp = event_timestamp.replace(tzinfo=timezone.utc)
            else:
                event_timestamp = event_timestamp.astimezone(timezone.utc)
        else:
            event_timestamp = datetime.now(timezone.utc)
    except ValueError:
        return jsonify({"error": "Invalid 'timestamp' format for event. Use ISO 8601 format."}), 400

    details_dict = data.get('details')
    details_str = None
    if details_dict is not None:
        if not isinstance(details_dict, dict):
            return jsonify({"error": "'details' for event must be a JSON object (dict)"}), 400
        try:
            details_str = json.dumps(details_dict)
        except TypeError:
            return jsonify({"error": "Failed to serialize 'details' for event to JSON string"}), 400

    now_utc = datetime.now(timezone.utc)
    created_at = now_utc
    updated_at = now_utc

    try:
        parent_key = db_client.key('employees', employee_id)
        event_key = db_client.key('employee_event', parent=parent_key) 
        
        event_entity = datastore.Entity(key=event_key)
        event_entity.update({
            'timestamp': event_timestamp, 'event_type': event_type,
            'description': description, 'created_at': created_at,
            'updated_at': updated_at
        })
        if details_str is not None:
            event_entity['details'] = details_str
        db_client.put(event_entity)
        
        generated_event_id = str(event_entity.key.id) 
        response_data = {
            "event_id": generated_event_id, "employee_id": employee_id,
            "timestamp": event_timestamp.isoformat(), "event_type": event_type,
            "description": description, "details": details_dict, 
            "created_at": created_at.isoformat(), "updated_at": updated_at.isoformat()
        }
        return jsonify(response_data), 201
    except Exception as e:
        current_app.logger.error(f"Error creating employee event for {employee_id}: {e}") 
        traceback.print_exc()
        return jsonify({"error": "Internal Server Error during event creation"}), 500