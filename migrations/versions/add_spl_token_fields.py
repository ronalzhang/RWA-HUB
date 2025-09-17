"""Add SPL Token fields to Asset model

Revision ID: add_spl_token_fields
Revises: previous_revision
Create Date: 2025-09-16 17:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_spl_token_fields'
down_revision = 'f1cd4dee1cd5'
branch_labels = None
depends_on = None


def upgrade():
    """Add SPL Token related fields to assets table"""

    # Add SPL Token fields to assets table
    with op.batch_alter_table('assets') as batch_op:
        batch_op.add_column(sa.Column('spl_mint_address', sa.String(44), nullable=True))
        batch_op.add_column(sa.Column('mint_authority_keypair', sa.Text, nullable=True))
        batch_op.add_column(sa.Column('freeze_authority_keypair', sa.Text, nullable=True))
        batch_op.add_column(sa.Column('metadata_uri', sa.String(500), nullable=True))
        batch_op.add_column(sa.Column('spl_creation_status', sa.Integer, default=0))
        batch_op.add_column(sa.Column('spl_creation_tx_hash', sa.String(128), nullable=True))
        batch_op.add_column(sa.Column('spl_created_at', sa.DateTime, nullable=True))

        # Add unique constraint for spl_mint_address
        batch_op.create_unique_constraint('uq_assets_spl_mint_address', ['spl_mint_address'])


def downgrade():
    """Remove SPL Token related fields from assets table"""

    with op.batch_alter_table('assets') as batch_op:
        # Drop unique constraint first
        batch_op.drop_constraint('uq_assets_spl_mint_address', type_='unique')

        # Remove columns
        batch_op.drop_column('spl_created_at')
        batch_op.drop_column('spl_creation_tx_hash')
        batch_op.drop_column('spl_creation_status')
        batch_op.drop_column('metadata_uri')
        batch_op.drop_column('freeze_authority_keypair')
        batch_op.drop_column('mint_authority_keypair')
        batch_op.drop_column('spl_mint_address')