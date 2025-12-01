"""add oauth support to users

Revision ID: oauth_support_001
Revises: add_last_login_at_to_users
Create Date: 2025-12-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'oauth_support_001'
down_revision = 'add_last_login_at_to_users'
branch_labels = None
depends_on = None


def upgrade():
    # Make password_hash nullable for OAuth users
    op.alter_column('users', 'password_hash',
                    existing_type=sa.String(length=255),
                    nullable=True)
    
    # Add OAuth fields
    op.add_column('users', sa.Column('oauth_provider', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('oauth_id', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('profile_picture', sa.String(length=500), nullable=True))
    
    # Create index on oauth_id for faster lookups
    op.create_index(op.f('ix_users_oauth_id'), 'users', ['oauth_id'], unique=False)


def downgrade():
    # Remove index
    op.drop_index(op.f('ix_users_oauth_id'), table_name='users')
    
    # Remove OAuth fields
    op.drop_column('users', 'profile_picture')
    op.drop_column('users', 'oauth_id')
    op.drop_column('users', 'oauth_provider')
    
    # Make password_hash required again (note: this may fail if OAuth users exist)
    op.alter_column('users', 'password_hash',
                    existing_type=sa.String(length=255),
                    nullable=False)

