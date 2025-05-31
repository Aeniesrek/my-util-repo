# app/google_meet_maps/__init__.py
from flask import Blueprint

google_meet_map_bp = Blueprint('google_meet_map', __name__, url_prefix='/google_meet_employee_map')

from . import routes # この行で同階層のroutes.pyを読み込み、ルート定義をブループリントに紐付ける