# app/meeting_summary/models.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class Decision:
    """会議で合意または方向性が示された決定事項を表すクラス。"""
    item: str # 決定事項の具体的な内容
    discussion_summary: str # その決定事項に至るまでの議論の要約
    source_utterance_indices: Optional[List[int]] = field(default_factory=list) # 関連する発言の source_index

@dataclass
class ActionItem:
    """会議で決まった次のアクションを表すクラス。"""
    action: str # 具体的なアクション内容
    assignee: str # 担当者
    due_date: Optional[str] = None # 期限 (ISO 8601形式の文字列を想定)

@dataclass
class MeetingSummary:
    """会議の要約全体を表すクラス。普遍的な1on1ミーティングの結果をシンプルに表現。"""
    meeting_date: str # 会議日時 (例: "2025-05-22 17:28 JST" or "2025-05-22T17:28:00+09:00")
    employee_name: str # ★変更: 会議の報告者（部下）の名前
    purpose: str # 会議の目的
    decisions: List[Decision] # 主要な決定事項のリスト
    action_items: List[ActionItem] # アクションアイテムのリスト
    overall_summary: str # 会議全体の主要な議論や結論の簡潔なまとめ