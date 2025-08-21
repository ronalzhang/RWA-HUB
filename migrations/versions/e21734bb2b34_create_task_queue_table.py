"""create task queue table

Revision ID: e21734bb2b34
Revises: a656379db413
Create Date: 2025-08-21 15:24:38.124914

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = 'e21734bb2b34'
down_revision = 'a656379db413'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('task_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_name', sa.String(length=128), nullable=False),
        sa.Column('task_args', JSONB(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_task_queue_status'), 'task_queue', ['status'], unique=False)
    op.create_index(op.f('ix_task_queue_created_at'), 'task_queue', ['created_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_task_queue_created_at'), table_name='task_queue')
    op.drop_index(op.f('ix_task_queue_status'), table_name='task_queue')
    op.drop_table('task_queue')