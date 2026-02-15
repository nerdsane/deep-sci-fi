"""Switch all content to critical_review system.

All new content should use the critical review system. Existing content
was incorrectly defaulting to legacy because the model default wasn't
updated when the system was deployed.

Revision ID: 0013
Revises: 0012
"""
from alembic import op

# revision identifiers
revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

TABLES = [
    "platform_proposals",
    "platform_aspects",
    "platform_stories",
    "platform_dweller_proposals",
]


def upgrade() -> None:
    for table in TABLES:
        op.execute(
            f"UPDATE {table} SET review_system = 'CRITICAL_REVIEW' WHERE review_system = 'LEGACY'"
        )


def downgrade() -> None:
    for table in TABLES:
        op.execute(
            f"UPDATE {table} SET review_system = 'LEGACY' WHERE review_system = 'CRITICAL_REVIEW'"
        )
