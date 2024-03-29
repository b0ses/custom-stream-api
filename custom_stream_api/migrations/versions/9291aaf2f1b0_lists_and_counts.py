"""lists and counts

Revision ID: 9291aaf2f1b0
Revises: ea75d5756f19
Create Date: 2019-03-17 10:59:16.539254

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9291aaf2f1b0'
down_revision = 'ea75d5756f19'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('count',
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('count', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('name')
    )
    op.create_table('list',
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('current_index', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('name')
    )
    op.create_table('list_item',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('list_name', sa.Text(), nullable=False),
    sa.Column('index', sa.Integer(), nullable=False),
    sa.Column('item', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['list_name'], ['list.name'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('list_name', 'index', name='_lists_uc')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('list_item')
    op.drop_table('list')
    op.drop_table('count')
    # ### end Alembic commands ###
