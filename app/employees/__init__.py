# app/employees/__init__.py

from flask import Blueprint

# app/employees/__init__.py
employees_bp = Blueprint('employee_management_routes', __name__, url_prefix='/employees')

# このBlueprintのルート定義をインポート
from . import routes