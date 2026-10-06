"""Entry point cho bản đóng gói desktop — chạy backend như process độc lập.

Phân biệt production qua env WRITER_ENV=production (launcher set) để
database/secret rơi vào user-data dir thay vì cwd.
"""
import os

os.environ.setdefault("ENVIRONMENT", os.environ.get("WRITER_ENV", "production"))

import uvicorn
from app.main import app

if __name__ == "__main__":
    port = int(os.environ.get("WRITER_PORT", "8765"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
