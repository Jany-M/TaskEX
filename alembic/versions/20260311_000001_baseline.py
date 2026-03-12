"""baseline revision for runtime migrations

Revision ID: 20260311_000001
Revises:
Create Date: 2026-03-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260311_000001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Baseline is intentionally empty; SQLAlchemy create_all handles existing schema.
    pass


def downgrade() -> None:
    pass
