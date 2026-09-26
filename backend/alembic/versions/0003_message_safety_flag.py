"""mark assistant messages that are safety responses

Revision ID: 0003_message_safety_flag
Revises: 0002_screening_status
Create Date: 2026-09-25

Safety *matches* stay ephemeral (nothing about the user's message is flagged
or stored). This column only marks that the assistant's reply came from the
safety library, so a restored conversation can still render it distinctly.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_message_safety_flag"
down_revision: Union[str, None] = "0002_screening_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column(
            "is_safety",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("messages", "is_safety")
