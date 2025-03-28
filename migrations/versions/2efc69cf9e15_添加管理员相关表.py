"""添加管理员相关表

Revision ID: 2efc69cf9e15
Revises: f1cd4dee1cd5
Create Date: 2025-03-16 11:37:57.532840

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2efc69cf9e15'
down_revision = 'f1cd4dee1cd5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('admin_operation_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('admin_address', sa.String(length=100), nullable=False),
    sa.Column('operation_type', sa.String(length=50), nullable=False),
    sa.Column('target_table', sa.String(length=50), nullable=True),
    sa.Column('target_id', sa.Integer(), nullable=True),
    sa.Column('operation_details', sa.Text(), nullable=True),
    sa.Column('ip_address', sa.String(length=50), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('admin_operation_logs', schema=None) as batch_op:
        batch_op.create_index('ix_admin_operation_logs_admin_address', ['admin_address'], unique=False)
        batch_op.create_index('ix_admin_operation_logs_created_at', ['created_at'], unique=False)
        batch_op.create_index('ix_admin_operation_logs_operation_type', ['operation_type'], unique=False)

    op.create_table('admin_users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('wallet_address', sa.String(length=100), nullable=False),
    sa.Column('username', sa.String(length=50), nullable=True),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('permissions', sa.Text(), nullable=True),
    sa.Column('last_login', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('wallet_address')
    )
    with op.batch_alter_table('admin_users', schema=None) as batch_op:
        batch_op.create_index('ix_admin_users_role', ['role'], unique=False)
        batch_op.create_index('ix_admin_users_wallet_address', ['wallet_address'], unique=False)

    op.create_table('commission_records',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('transaction_id', sa.String(length=100), nullable=False),
    sa.Column('asset_id', sa.Integer(), nullable=True),
    sa.Column('recipient_address', sa.String(length=100), nullable=False),
    sa.Column('amount', sa.Numeric(precision=18, scale=8), nullable=False),
    sa.Column('currency', sa.String(length=10), nullable=False),
    sa.Column('commission_type', sa.String(length=20), nullable=False),
    sa.Column('referral_level', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('commission_records', schema=None) as batch_op:
        batch_op.create_index('ix_commission_records_created_at', ['created_at'], unique=False)
        batch_op.create_index('ix_commission_records_recipient_address', ['recipient_address'], unique=False)
        batch_op.create_index('ix_commission_records_status', ['status'], unique=False)
        batch_op.create_index('ix_commission_records_transaction_id', ['transaction_id'], unique=False)

    op.create_table('commission_settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('asset_type_id', sa.Integer(), nullable=True),
    sa.Column('commission_rate', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('min_amount', sa.Numeric(precision=18, scale=8), nullable=True),
    sa.Column('max_amount', sa.Numeric(precision=18, scale=8), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_by', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('commission_settings', schema=None) as batch_op:
        batch_op.create_index('ix_commission_settings_asset_type_id', ['asset_type_id'], unique=False)
        batch_op.create_index('ix_commission_settings_is_active', ['is_active'], unique=False)

    op.create_table('dashboard_stats',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('stat_date', sa.Date(), nullable=False),
    sa.Column('stat_type', sa.String(length=50), nullable=False),
    sa.Column('stat_value', sa.Float(), nullable=False),
    sa.Column('stat_period', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('dashboard_stats', schema=None) as batch_op:
        batch_op.create_index('ix_dashboard_stats_date_type_period', ['stat_date', 'stat_type', 'stat_period'], unique=True)
        batch_op.create_index('ix_dashboard_stats_stat_date', ['stat_date'], unique=False)

    op.create_table('distribution_levels',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('level', sa.Integer(), nullable=False),
    sa.Column('commission_rate', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('distribution_levels', schema=None) as batch_op:
        batch_op.create_index('ix_distribution_levels_is_active', ['is_active'], unique=False)
        batch_op.create_index('ix_distribution_levels_level', ['level'], unique=False)

    op.create_table('system_configs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('config_key', sa.String(length=50), nullable=False),
    sa.Column('config_value', sa.Text(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('config_key')
    )
    with op.batch_alter_table('system_configs', schema=None) as batch_op:
        batch_op.create_index('ix_system_configs_config_key', ['config_key'], unique=False)

    op.create_table('user_referrals',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_address', sa.String(length=100), nullable=False),
    sa.Column('referrer_address', sa.String(length=100), nullable=False),
    sa.Column('referral_level', sa.Integer(), nullable=False),
    sa.Column('referral_code', sa.String(length=50), nullable=True),
    sa.Column('joined_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('user_referrals', schema=None) as batch_op:
        batch_op.create_index('ix_user_referrals_referral_code', ['referral_code'], unique=False)
        batch_op.create_index('ix_user_referrals_referrer_address', ['referrer_address'], unique=False)
        batch_op.create_index('ix_user_referrals_user_address', ['user_address'], unique=False)

    op.create_table('dividends',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('asset_id', sa.Integer(), nullable=False),
    sa.Column('amount', sa.Float(), nullable=False),
    sa.Column('distribution_date', sa.DateTime(), nullable=False),
    sa.Column('record_date', sa.DateTime(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('transaction_hash', sa.String(length=100), nullable=True),
    sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('platform_income',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('income_type', sa.String(length=20), nullable=False, comment='收入类型: trade_fee, onchain_fee, dividend_fee, other'),
    sa.Column('amount', sa.Float(), nullable=False, comment='收入金额'),
    sa.Column('currency', sa.String(length=10), nullable=False, comment='收入币种'),
    sa.Column('created_at', sa.DateTime(), nullable=False, comment='收入记录创建时间'),
    sa.Column('description', sa.String(length=255), nullable=True, comment='收入描述'),
    sa.Column('transaction_hash', sa.String(length=100), nullable=True, comment='交易哈希'),
    sa.Column('asset_id', sa.Integer(), nullable=True, comment='关联资产ID'),
    sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('platform_incomes', schema=None) as batch_op:
        batch_op.drop_index('ix_platform_incomes_type')

    with op.batch_alter_table('trades', schema=None) as batch_op:
        batch_op.alter_column('tx_hash',
               existing_type=sa.VARCHAR(length=66),
               type_=sa.String(length=100),
               existing_nullable=True)
        batch_op.alter_column('status',
               existing_type=sa.VARCHAR(length=20),
               nullable=True,
               existing_server_default=sa.text("'pending'::character varying"))
        batch_op.alter_column('created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('trades', schema=None) as batch_op:
        batch_op.alter_column('created_at',
               existing_type=postgresql.TIMESTAMP(),
               nullable=False)
        batch_op.alter_column('status',
               existing_type=sa.VARCHAR(length=20),
               nullable=False,
               existing_server_default=sa.text("'pending'::character varying"))
        batch_op.alter_column('tx_hash',
               existing_type=sa.String(length=100),
               type_=sa.VARCHAR(length=66),
               existing_nullable=True)

    with op.batch_alter_table('platform_incomes', schema=None) as batch_op:
        batch_op.create_index('ix_platform_incomes_type', ['type'], unique=False)

    op.drop_table('platform_income')
    op.drop_table('dividends')
    with op.batch_alter_table('user_referrals', schema=None) as batch_op:
        batch_op.drop_index('ix_user_referrals_user_address')
        batch_op.drop_index('ix_user_referrals_referrer_address')
        batch_op.drop_index('ix_user_referrals_referral_code')

    op.drop_table('user_referrals')
    with op.batch_alter_table('system_configs', schema=None) as batch_op:
        batch_op.drop_index('ix_system_configs_config_key')

    op.drop_table('system_configs')
    with op.batch_alter_table('distribution_levels', schema=None) as batch_op:
        batch_op.drop_index('ix_distribution_levels_level')
        batch_op.drop_index('ix_distribution_levels_is_active')

    op.drop_table('distribution_levels')
    with op.batch_alter_table('dashboard_stats', schema=None) as batch_op:
        batch_op.drop_index('ix_dashboard_stats_stat_date')
        batch_op.drop_index('ix_dashboard_stats_date_type_period')

    op.drop_table('dashboard_stats')
    with op.batch_alter_table('commission_settings', schema=None) as batch_op:
        batch_op.drop_index('ix_commission_settings_is_active')
        batch_op.drop_index('ix_commission_settings_asset_type_id')

    op.drop_table('commission_settings')
    with op.batch_alter_table('commission_records', schema=None) as batch_op:
        batch_op.drop_index('ix_commission_records_transaction_id')
        batch_op.drop_index('ix_commission_records_status')
        batch_op.drop_index('ix_commission_records_recipient_address')
        batch_op.drop_index('ix_commission_records_created_at')

    op.drop_table('commission_records')
    with op.batch_alter_table('admin_users', schema=None) as batch_op:
        batch_op.drop_index('ix_admin_users_wallet_address')
        batch_op.drop_index('ix_admin_users_role')

    op.drop_table('admin_users')
    with op.batch_alter_table('admin_operation_logs', schema=None) as batch_op:
        batch_op.drop_index('ix_admin_operation_logs_operation_type')
        batch_op.drop_index('ix_admin_operation_logs_created_at')
        batch_op.drop_index('ix_admin_operation_logs_admin_address')

    op.drop_table('admin_operation_logs')
    # ### end Alembic commands ###
