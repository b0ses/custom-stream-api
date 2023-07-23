"""Adding created_ats to models

Revision ID: d11236dc9b5d
Revises: 173a43722420
Create Date: 2022-08-21 17:16:36.400259

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'd11236dc9b5d'
down_revision = '173a43722420'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('alert', sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.add_column('alias', sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.add_column('count', sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.add_column('group_alert', sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.add_column('list', sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.add_column('timer', sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('timer', 'created_at')
    op.drop_column('list', 'created_at')
    op.drop_column('group_alert', 'created_at')
    op.drop_column('count', 'created_at')
    op.drop_column('alias', 'created_at')
    op.drop_column('alert', 'created_at')
    # ### end Alembic commands ###
