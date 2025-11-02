"""Adding booleans to timers

Revision ID: 442337e12ebe
Revises: de70b83f2201
Create Date: 2025-11-01 22:16:09.904767

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '442337e12ebe'
down_revision = 'de70b83f2201'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('timer', sa.Column('repeat', sa.Boolean(), server_default='t', nullable=False))
    op.add_column('timer', sa.Column('active', sa.Boolean(), server_default='t', nullable=False))
    # ### end Alembic commands ###


def downgrade():
    op.drop_column('timer', 'active')
    op.drop_column('timer', 'repeat')
    # ### end Alembic commands ###
