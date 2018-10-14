"""empty message

Revision ID: b8d26adc94bd
Revises: 
Create Date: 2018-10-09 23:37:06.303364

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b8d26adc94bd'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('alert',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=True),
    sa.Column('text', sa.String(length=128), nullable=True),
    sa.Column('sound', sa.String(length=128), nullable=True),
    sa.Column('image', sa.String(length=128), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('alert')
    # ### end Alembic commands ###