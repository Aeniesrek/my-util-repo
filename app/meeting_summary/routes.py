# app/meeting_summary/routes.py

import os
import requests
import json
from datetime import datetime, timezone
from typing import List, Dict
from dataclasses import asdict

from flask import Blueprint, request, jsonify, current_app
from app.auth import authenticate_request 
import google.generativeai as genai
import google.generativeai.types as genai_types
from google.cloud import datastore 
from datetime import datetime, timezone 
import json
from typing import List, Dict, Optional 
from dataclasses import asdict 

from app.meeting_summary.models import MeetingSummary, Decision, ActionItem

# Blueprintの定義
bp = Blueprint('meeting_summary', __name__) 

def _format_summary_for_slack(summary: MeetingSummary) -> str:
    """MeetingSummaryオブジェクトをSlack投稿用に整形する"""

    # ActionItemをリスト形式のテキストに変換
    action_items_text = "\n".join(
        [f"- {item.action} (担当: {item.assignee}, 期限: {item.due_date})" for item in summary.action_items]
    ) if summary.action_items else "なし"

    # Decisionをリスト形式のテキストに変換
    decisions_text = "\n".join(
        [f"- {decision.item}" for decision in summary.decisions]
    ) if summary.decisions else "なし"

    # Slackメッセージのテキスト全体を組み立てる
    text = f"""
:notebook: *1on1ミーティング 議事録サマリー*

*参加者*: {summary.employee_name if summary.employee_name else '未指定'}
*会議日*: {summary.meeting_date if summary.meeting_date else '未指定'}
*目的*: {summary.purpose if summary.purpose else '未指定'}
---
*決定事項*
{decisions_text}
---
*アクションアイテム*
{action_items_text}
---
*全体サマリー*
{summary.overall_summary}
    """
    return text.strip()


def _post_summary_to_slack(summary: MeetingSummary):
    """整形された議事録サマリーをSlackに投稿する"""
    slack_token = os.getenv('SLACK_TOKEN')
    slack_channel = os.getenv('SLACK_CHANNEL')

    if not slack_token or not slack_channel:
        current_app.logger.warning("SLACK_TOKEN or SLACK_CHANNEL is not set. Skipping Slack post.")
        return

    message_text = _format_summary_for_slack(summary)
    
    headers = {
        "Authorization": f"Bearer {slack_token}",
        "Content-Type": "application/json; charset=utf-8"
    }
    payload = {
        "channel": slack_channel,
        "text": message_text,
        "unfurl_links": False, # リンクのプレビューを無効化
    }
    
    try:
        response = requests.post("https://slack.com/api/chat.postMessage", headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        response_data = response.json()
        if response_data.get("ok"):
            current_app.logger.info(f"Successfully posted summary to Slack channel {slack_channel}")
        else:
            current_app.logger.error(f"Slack API error: {response_data.get('error')}")
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Failed to post message to Slack: {e}")

# --- Function Calling用のツール関数の定義 ---
def create_meeting_summary_tool_function(
    meeting_date: str,
    employee_name: str,
    purpose: str,
    decisions: List[Dict], 
    overall_summary: str,
    action_items: List[Dict], 
) -> Dict:
    """
    会議の議事録データから主要な情報を抽出し、構造化されたサマリーを生成します。
    この関数は、言語モデルが呼び出すためのスキーマとして使用されます。
    """
    return {
        "meeting_date": meeting_date,
        "employee_name": employee_name,
        "purpose": purpose,
        "decisions": decisions,
        "overall_summary": overall_summary,
        "action_items": action_items,
    }

# --- ヘルパー関数: Compositeオブジェクトを標準のPython型に再帰的に変換 ---
def _to_plain_python_types(obj):
    """
    Google Generative AIのレスポンスに含まれるCompositeオブジェクトを
    標準のPython辞書やリストに再帰的に変換します。
    """
    if isinstance(obj, dict) or (hasattr(obj, 'items') and not isinstance(obj, type)): 
        return {k: _to_plain_python_types(v) for k, v in obj.items()}
    elif isinstance(obj, list) or (hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, type))): 
        return [_to_plain_python_types(elem) for elem in obj]
    else:
        return obj

# --- 要約エンドポイント ---
@bp.route('/meeting', methods=['POST'])
@authenticate_request # 認証を適用
def summarize_meeting():
    """
    1on1議事録テキストを受け取り、Google Generative AIのFunction Callingを用いて要約を生成し、
    その結果をJSONで返すエンドポイント。
    オプションでFirestoreにも保存する。
    """
    data = request.get_json()
    if not data or 'transcript_content' not in data:
        current_app.logger.error("Invalid request body: 'transcript_content' is required.")
        return jsonify({"message": "Invalid request body: 'transcript_content' is required"}), 400

    transcript_content = data['transcript_content']
    save_to_firestore = data.get('save_to_firestore', False) 

    #post_to_slack = data.get('post_to_slack', False)
    post_to_slack = True # ★変更: Slackへの投稿を常に有効化

    try:
        model = genai.GenerativeModel(
            'gemini-2.0-flash', 
            tools=[create_meeting_summary_tool_function]
        )
    except Exception as e:
        current_app.logger.error(f"Failed to initialize GenerativeModel: {e}")
        return jsonify({"message": "Internal server error: Could not initialize AI model"}), 500
    
    prompt = f"""
    以下の1on1会議の文字起こしデータから、指定された形式で情報を抽出し、要約してください。
    出力は`create_meeting_summary_tool_function`関数を呼び出す形式で出力してください。

    ---
    会議の文字起こしデータ:
    {transcript_content}
    ---

    抽出・要約する項目は以下の通りです。
    1.  **会議日時**: 文字起こしファイル名または内容から正確な日時を抽出してください。フォーマットは"YYYY-MM-DD HH:MM JST"または"YYYY-MM-DDTHH:MM:SS+09:00"のように、可能な限りISO 8601に近い形でお願いします。
    2.  **社員名**: このミーティングの参加者の名前を厳密に抽出してください。**森口裕之は上司なので除外してください。**
    3.  **会議の目的**: 会議の目的を具体的に要約してください。
    4.  **決定事項**: 会議で合意された、あるいは方向性が示された主要な決定事項をリストアップしてください。各決定事項について、内容、そしてその決定に至るまでの議論の要約を含めてください。関連する発言の`source_index`（のxの値）があれば整数値のリストで含めてください。
       **決定事項の各項目は、`item` (内容)、`discussion_summary` (議論の要約)、`source_utterance_indices` (関連インデックス) のキーを持つ辞書として記述してください。**
    5.  **全体要約**: 会議全体の主要なポイント、結論、方向性、および主要な議論の要約を簡潔にまとめてください。
    6.  **アクションアイテム**: 会議で決まった具体的な次のアクションをリストアップしてください。担当者も明確にしてください。期限があれば"YYYY-MM-DD"形式で記載してください。
       **アクションアイテムの各項目は、`action` (内容)、`assignee` (担当者)、`due_date` (期限) のキーを持つ辞書として記述してください。**

    """

    try:
        response = model.generate_content(prompt)

        if response.candidates:
            candidate = response.candidates[0]
            if candidate.finish_reason == 'SAFETY' or (candidate.finish_reason and candidate.safety_ratings):
                current_app.logger.warning("Generative AI response was blocked due to safety settings.")
                safety_details = []
                if candidate.safety_ratings:
                    for rating in candidate.safety_ratings:
                        safety_details.append(f"{rating.category.name}: {rating.probability.name}")
                return jsonify({
                    "message": "Could not summarize. AI response blocked due to safety settings.", 
                    "details": "Please check transcript content for sensitive information.",
                    "safety_ratings": safety_details,
                    "raw_response": str(candidate)
                }), 400
            
            if candidate.content and candidate.content.parts:
                part = candidate.content.parts[0]
                if part.function_call:
                    function_call_args_plain = _to_plain_python_types(part.function_call.args)
                    current_app.logger.info(f"Function Call Args (Plain): {json.dumps(function_call_args_plain, indent=2, ensure_ascii=False)}")

                    decisions_raw = function_call_args_plain.get('decisions', [])
                    decisions = []
                    for d_item in decisions_raw:
                        mapped_d = {
                            'item': d_item.get('item') or d_item.get('content', ''), 
                            'discussion_summary': d_item.get('discussion_summary', ''),
                            'source_utterance_indices': d_item.get('source_utterance_indices', [])
                        }
                        filtered_d = {k: v for k, v in mapped_d.items() if k in Decision.__annotations__}
                        decisions.append(Decision(**filtered_d))

                    action_items_raw = function_call_args_plain.get('action_items', [])
                    action_items = []
                    for a_item in action_items_raw:
                        filtered_a = {k: v for k, v in a_item.items() if k in ActionItem.__annotations__}
                        action_items.append(ActionItem(**filtered_a))

                    summary_data = MeetingSummary(
                        meeting_date=function_call_args_plain.get('meeting_date', ''),
                        employee_name=function_call_args_plain.get('employee_name', ''), # ★変更
                        purpose=function_call_args_plain.get('purpose', ''),
                        decisions=decisions,
                        overall_summary=function_call_args_plain.get('overall_summary', ''),
                        action_items=action_items,
                    )
                    print("Posting summary to Slack...",post_to_slack)
                    if post_to_slack:
                        
                        _post_summary_to_slack(summary_data)

                    if save_to_firestore:
                        db_client = current_app.db 
                        if not db_client:
                            current_app.logger.error("Datastore client not initialized for saving summary.")
                            return jsonify({"message": "Internal server error: Datastore client not initialized"}), 500

                        kind = '1on1_summaries' 
                        meeting_id_str = f"1on1_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}" 
                        key = db_client.key(kind, meeting_id_str) 

                        entity = datastore.Entity(key=key) 
                        
                        doc_data = asdict(summary_data)
                        doc_data["createdAt"] = datetime.now(timezone.utc) 

                        entity.update(doc_data)
                        
                        db_client.put(entity) 
                        current_app.logger.info(f"Meeting summary saved to Datastore: {meeting_id_str}")
                        return jsonify({"message": "Meeting summary generated and saved", "summary": summary_data.__dict__}), 200
                    else:
                        return jsonify({"message": "Meeting summary generated", "summary": summary_data.__dict__}), 200
                else:
                    current_app.logger.warning("Generative AI did not produce a function call. It returned text content instead.")
                    text_response = part.text if hasattr(part, 'text') else 'No text part'
                    current_app.logger.info(f"AI raw text response: {text_response}")
                    return jsonify({"message": "Could not summarize meeting transcript as expected. AI returned text instead of function call.", "raw_response": text_response}), 500
            else:
                current_app.logger.warning("Generative AI response candidate has no content or parts.")
                return jsonify({"message": "Could not summarize meeting transcript. AI response was empty or malformed.", "raw_response": str(candidate)}), 500
        else:
            current_app.logger.warning("Generative AI response had no candidates. Likely blocked by safety settings.")
            return jsonify({"message": "Could not summarize meeting transcript. AI response was blocked or empty.", "raw_response": str(response)}), 500

    except genai.types.BlockedPromptException as e:
        current_app.logger.error(f"Prompt was blocked by safety settings: {e}")
        return jsonify({"message": "Prompt was blocked by safety settings.", "details": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error summarizing meeting transcript: {e}", exc_info=True)
        return jsonify({"message": f"Internal server error: {str(e)}"}), 500
