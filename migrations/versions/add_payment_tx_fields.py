"""add_payment_tx_fields

Revision ID: 91f4a8c7e9d3
Revises: 98fa7c6d1e32
Create Date: 2025-05-17 23:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '91f4a8c7e9d3'
down_revision = '98fa7c6d1e32'  # 更新为最新的迁移版本
branch_labels = None
depends_on = None


def upgrade():
    # 添加payment_tx_hash字段到assets表
    op.add_column('assets', sa.Column('payment_tx_hash', sa.String(255), nullable=True))
    # 注意：其他支付相关字段(payment_details, payment_confirmed, payment_confirmed_at)
    # 已经在之前的迁移中添加，所以我们只需要添加payment_tx_hash


def downgrade():
    # 移除添加的列
    op.drop_column('assets', 'payment_tx_hash') 