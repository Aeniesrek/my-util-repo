# app/main/__init__.py

from flask import Blueprint

main_bp = Blueprint('myutil_main', __name__) 

# このBlueprintのルート定義をインポート (このファイルの最後に書くのが一般的)
from . import routes