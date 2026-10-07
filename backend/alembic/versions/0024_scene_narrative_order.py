"""Backfill scenes.narrative_order + chuẩn hoá story_states.key về canonical
(location/lifecycle/ownership) để constraint engine neo đúng vị trí truyện.

narrative_order = chapter.order_index (convention codebase: manuscript.py và
knowledge-leak đều so ở chapter scale) — axis mà states_at/build_constraints
lọc state trích từ chương sau ra khỏi cảnh trước."""
from alembic import op
import sqlalchemy as sa

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None

# free-text key extractor hay ghi → key canonical mà constraints hiểu
_KEY_MAP = {
    "nơi ở": "location", "địa điểm": "location", "vị trí": "location",
    "hiện diện": "location", "nơi ở hiện tại": "location",
    "vị trí hiện tại": "location",
    "sinh tử": "lifecycle", "sống/chết": "lifecycle",
    "hiện trạng sống": "lifecycle", "trạng thái sống": "lifecycle",
    "sở hữu": "ownership", "thuộc về": "ownership", "chủ sở hữu": "ownership",
    "tuổi": "age", "độ tuổi": "age", "tuổi hiện tại": "age",
    "lứa tuổi": "age", "năm sinh": "age",
    "lớp": "education", "lớp học": "education", "lớp_học": "education",
    "khối": "education", "học lớp": "education", "trường học": "education",
    "trường_học": "education", "trường": "education", "năm học": "education",
    "cấp học": "education", "năm nay lên lớp": "education",
}


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "UPDATE scenes SET narrative_order = ("
        "  SELECT c.order_index FROM chapters c"
        "  WHERE c.id = scenes.chapter_id"
        ") WHERE chapter_id IS NOT NULL"))
    for raw, canon in _KEY_MAP.items():
        conn.execute(sa.text(
            "UPDATE story_states SET key = :canon WHERE lower(key) = :raw"),
            {"canon": canon, "raw": raw})


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE scenes SET narrative_order = NULL"))
    for raw, canon in _KEY_MAP.items():
        conn.execute(sa.text(
            "UPDATE story_states SET key = :raw WHERE key = :canon"),
            {"raw": raw, "canon": canon})
