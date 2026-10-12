"""Seed dữ liệu demo lần đầu chạy — chỉ khi projects rỗng (cài mới tinh).

seed_data/ chứa export .json đã gắn mác [DEMO]; import qua cùng logic với
endpoint /projects/import (remap id an toàn). Chạy được ở dev lẫn bundle:
dev → backend/seed_data, PyInstaller → _MEIPASS/seed_data.
"""
import json, logging
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project

log = logging.getLogger("seed_demo")

SEED_DIR = Path(__file__).resolve().parents[2] / "seed_data"


async def seed_if_empty(db: AsyncSession) -> int:
    """Trả số project đã seed. Idempotent theo thiết kế: chỉ chạy khi chưa
    có project nào — người dùng xoá hết demo cũng không bị seed lại."""
    n = (await db.scalar(select(func.count()).select_from(Project))) or 0
    if n or not SEED_DIR.is_dir():
        return 0
    from app.api.routes.export import do_import
    made = 0
    for f in sorted(SEED_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("format") != "ai-writer-studio-export":
                continue
            await do_import(db, data)
            made += 1
            log.info("seeded demo project: %s", f.name)
        except Exception:
            log.exception("seed %s failed — bỏ qua", f.name)
            await db.rollback()
    return made
