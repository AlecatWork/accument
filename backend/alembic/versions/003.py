"""Reading status, failure reasons, and token counts.

Adds:
  * documents.reading_status  - the reader's bookmark (to_read / reading / done) for the dashboard donut
  * documents.error_message   - a plain-English reason when a paper fails to process
  * query_logs.prompt_tokens / completion_tokens - how much the AI read and wrote per question

Existing rows keep working: every old paper starts as "to_read".

Revision ID: 003
Revises: 002
Create Date: 2026-11-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, Sequence[str], None] = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("reading_status", sa.String(length=16), nullable=False, server_default="to_read"),
    )
    op.add_column("documents", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("query_logs", sa.Column("prompt_tokens", sa.Integer(), nullable=True))
    op.add_column("query_logs", sa.Column("completion_tokens", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("query_logs", "completion_tokens")
    op.drop_column("query_logs", "prompt_tokens")
    op.drop_column("documents", "error_message")
    op.drop_column("documents", "reading_status")
