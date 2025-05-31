"""添加message_type字段到share_messages表

Revision ID: add_message_type_202501
Revises: 
Create Date: 2025-01-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_message_type_202501'
down_revision = None
depends_on = None

def upgrade():
    # 添加message_type字段
    with op.batch_alter_table('share_messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('message_type', sa.String(length=50), nullable=False, server_default='share_content'))

def downgrade():
    # 删除message_type字段
    with op.batch_alter_table('share_messages', schema=None) as batch_op:
        batch_op.drop_column('message_type') 