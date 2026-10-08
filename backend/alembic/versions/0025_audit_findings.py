"""audit_findings — lưu kết quả AI soi chương (deep-check) theo project.

issues_json: list [{code, severity, message, suggestion, scene_id?}].
Tách khỏi canon_facts vì đây là phát hiện AI chờ tác giả duyệt, không phải
sự thật truyện."""
from alembic import op
import sqlalchemy as sa

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_findings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), index=True),
        sa.Column("scope_type", sa.String(32), nullable=False, server_default="chapter"),
        sa.Column("scope_id", sa.String(36), nullable=False, index=True),
        sa.Column("issues_json", sa.Text, nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_findings")
