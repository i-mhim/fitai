"""Account ownership and persisted assessments.

Revision ID: 0001_auth_assessments
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_auth_assessments"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "assessment_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("goal_type", sa.String(40), nullable=False),
        sa.Column("target_value", sa.Integer, nullable=False),
        sa.Column("requested_weeks", sa.Integer, nullable=False),
        sa.Column("question_bank_version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("safety_flags", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assessment_sessions_user_id", "assessment_sessions", ["user_id"])
    op.create_table(
        "assessment_answers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("assessment_id", sa.String(36), sa.ForeignKey("assessment_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("question_id", sa.String(100), nullable=False),
        sa.Column("question_version", sa.Integer, nullable=False),
        sa.Column("value", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("assessment_id", "question_id", name="uq_assessment_question"),
        sa.UniqueConstraint("assessment_id", "position", name="uq_assessment_position"),
    )
    op.create_index("ix_assessment_answers_assessment_id", "assessment_answers", ["assessment_id"])


def downgrade():
    op.drop_index("ix_assessment_answers_assessment_id", table_name="assessment_answers")
    op.drop_table("assessment_answers")
    op.drop_index("ix_assessment_sessions_user_id", table_name="assessment_sessions")
    op.drop_table("assessment_sessions")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
