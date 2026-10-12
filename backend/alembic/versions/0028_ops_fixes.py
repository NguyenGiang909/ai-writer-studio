"""ops fixes từ biên bản vận hành:
- abilities.owner_character_id — kĩ năng gắn chủ nhân → auto-inject (C11)
- audit_findings.status/dismiss_key — dismiss finding để checker không flag lại (#10)
- ai_turns.latency_ms — đo latency mỗi call (C20)
- audit_jobs — deep-check chạy nền, poll status (C10)
"""
from alembic import op
import sqlalchemy as sa

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("abilities") as b:
        b.add_column(sa.Column("owner_character_id", sa.String(36), nullable=True))
        b.create_index("ix_abilities_owner_character_id", ["owner_character_id"])
    with op.batch_alter_table("audit_findings") as b:
        b.add_column(sa.Column("status", sa.String(16), nullable=False,
                               server_default="open"))
        b.add_column(sa.Column("dismiss_key", sa.String(120), nullable=True))
        b.create_index("ix_audit_findings_dismiss_key", ["dismiss_key"])
    with op.batch_alter_table("ai_turns") as b:
        b.add_column(sa.Column("latency_ms", sa.Integer(), nullable=True))
    op.create_table(
        "audit_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey(
            "projects.id", ondelete="CASCADE"), index=True),
        sa.Column("scope_type", sa.String(32), nullable=False, server_default="chapter"),
        sa.Column("scope_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="running"),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("finished_at", sa.String(40), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("audit_jobs")
    with op.batch_alter_table("ai_turns") as b:
        b.drop_column("latency_ms")
    with op.batch_alter_table("audit_findings") as b:
        b.drop_index("ix_audit_findings_dismiss_key")
        b.drop_column("dismiss_key")
        b.drop_column("status")
    with op.batch_alter_table("abilities") as b:
        b.drop_index("ix_abilities_owner_character_id")
        b.drop_column("owner_character_id")
