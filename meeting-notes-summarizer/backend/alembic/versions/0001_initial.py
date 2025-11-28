"""
Initial database schema for Meeting Notes Summarizer

Revision ID: 0001_initial
Revises: 
Create Date: 2025-11-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # meetings table
    op.create_table(
        'meetings',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('meeting_date', sa.DateTime(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('language', sa.String(length=10), nullable=True),
        sa.Column('duration_sec', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # transcripts table
    op.create_table(
        'transcripts',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id'), nullable=False, unique=True, index=True),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('clean_text', sa.Text(), nullable=True),
        sa.Column('file_name', sa.String(length=255), nullable=True),
        sa.Column('file_type', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # summaries table
    op.create_table(
        'summaries',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id'), nullable=False, index=True),
        sa.Column('style', sa.String(length=50), nullable=True),
        sa.Column('max_bullets', sa.Integer(), nullable=True),
        sa.Column('bullets_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # action_items table
    op.create_table(
        'action_items',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id'), nullable=False, index=True),
        sa.Column('task', sa.Text(), nullable=False),
        sa.Column('assignee', sa.String(length=255), nullable=True),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('priority', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('source_quote', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # decisions table
    op.create_table(
        'decisions',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id'), nullable=False, index=True),
        sa.Column('decision', sa.Text(), nullable=False),
        sa.Column('owner', sa.String(length=255), nullable=True),
        sa.Column('decision_date', sa.DateTime(), nullable=True),
        sa.Column('source_quote', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # tool_runs table
    op.create_table(
        'tool_runs',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id'), nullable=False, index=True),
        sa.Column('tool_name', sa.String(length=100), nullable=False),
        sa.Column('input_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('output_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('tool_runs')
    op.drop_table('decisions')
    op.drop_table('action_items')
    op.drop_table('summaries')
    op.drop_table('transcripts')
    op.drop_table('meetings')
    op.drop_table('users')


