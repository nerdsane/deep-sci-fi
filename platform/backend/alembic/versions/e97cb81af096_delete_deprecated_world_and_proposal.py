"""delete deprecated world and proposal

Revision ID: e97cb81af096
Revises: 0025
Create Date: 2026-02-19 14:44:15.625019

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e97cb81af096'
down_revision: Union[str, None] = '0025'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# World and proposal named "Deprecated" — created by mistake, needs cleanup.
# DB-level ON DELETE CASCADE on all child FKs handles stories, dwellers,
# aspects, events, feed_events, etc. automatically.
WORLD_ID = 'd560fad9-9e92-4ba1-ae35-4fa3b108de75'
PROPOSAL_ID = 'd91678ae-c700-47a9-97bf-84ff2fb95355'


def upgrade() -> None:
    conn = op.get_bind()

    # Delete world first (CASCADE handles all children)
    result = conn.execute(
        sa.text("DELETE FROM platform_worlds WHERE id = :id"),
        {"id": WORLD_ID},
    )
    if result.rowcount:
        print(f"  Deleted world {WORLD_ID} (and cascaded children)")

    # Delete proposal (CASCADE handles validations)
    result = conn.execute(
        sa.text("DELETE FROM platform_proposals WHERE id = :id"),
        {"id": PROPOSAL_ID},
    )
    if result.rowcount:
        print(f"  Deleted proposal {PROPOSAL_ID} (and cascaded validations)")


def downgrade() -> None:
    # Data deletion is irreversible — no downgrade possible
    pass
