"""chapters.cast_json — dàn chương do tác giả khai báo (nhân vật/hố/năng lực)."""
from alembic import op
import sqlalchemy as sa

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("chapters") as b:
        b.add_column(sa.Column("cast_json", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("chapters") as b:
        b.drop_column("cast_json")
