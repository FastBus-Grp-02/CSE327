"""Add last_login_at field to users table

Revision ID: add_last_login_at_to_users
Revises: b55331da1623
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_last_login_at_to_users'
down_revision = 'b55331da1623'
branch_labels = None
depends_on = None


def upgrade():
    # Add last_login_at column to users table
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(), nullable=True))


def downgrade():
    # Remove last_login_at column from users table
    op.drop_column('users', 'last_login_at')


