"""Add directional relationship columns.

Extends platform_dweller_relationships with directional interaction signals:
- speak_count_a_to_b / speak_count_b_to_a: SPEAK actions between dwellers
- story_mention_a_to_b / story_mention_b_to_a: story perspective dweller mentions other
- thread_count: length of reply chains between the pair
- last_interaction_at: timestamp of most recent interaction

Revision ID: 0024
Revises: 0023
"""
from typing import Union
from alembic import op
import sqlalchemy as sa


revision = "0024"
down_revision = "0023"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :column"
    ), {"table": table_name, "column": column_name})
    return result.fetchone() is not None


def upgrade():
    table = "platform_dweller_relationships"

    if not column_exists(table, "speak_count_a_to_b"):
        op.add_column(table, sa.Column(
            "speak_count_a_to_b", sa.Integer(), nullable=False, server_default="0"
        ))
    if not column_exists(table, "speak_count_b_to_a"):
        op.add_column(table, sa.Column(
            "speak_count_b_to_a", sa.Integer(), nullable=False, server_default="0"
        ))
    if not column_exists(table, "story_mention_a_to_b"):
        op.add_column(table, sa.Column(
            "story_mention_a_to_b", sa.Integer(), nullable=False, server_default="0"
        ))
    if not column_exists(table, "story_mention_b_to_a"):
        op.add_column(table, sa.Column(
            "story_mention_b_to_a", sa.Integer(), nullable=False, server_default="0"
        ))
    if not column_exists(table, "thread_count"):
        op.add_column(table, sa.Column(
            "thread_count", sa.Integer(), nullable=False, server_default="0"
        ))
    if not column_exists(table, "last_interaction_at"):
        op.add_column(table, sa.Column(
            "last_interaction_at", sa.DateTime(timezone=True), nullable=True
        ))


def downgrade():
    table = "platform_dweller_relationships"
    for col in [
        "speak_count_a_to_b",
        "speak_count_b_to_a",
        "story_mention_a_to_b",
        "story_mention_b_to_a",
        "thread_count",
        "last_interaction_at",
    ]:
        if column_exists(table, col):
            op.drop_column(table, col)
