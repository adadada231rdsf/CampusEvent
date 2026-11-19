"""CampusEvent 开发服务器入口。

用法：
    python run.py            # http://127.0.0.1:5000
    set PORT=8000 && python run.py
生产环境用 gunicorn：gunicorn -b 0.0.0.0:80 "app:create_app()"
"""
from __future__ import annotations

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=bool(os.environ.get("FLASK_DEBUG")))
