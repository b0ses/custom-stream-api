"""adding group alert chat fields

Revision ID: 173a43722420
Revises: c4157102f944
Create Date: 2019-04-21 00:28:56.810956

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '173a43722420'
down_revision = 'c4157102f944'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("group_alert", sa.Column('chat_message', sa.String(length=128), nullable=True))
    with op.batch_alter_table("group_alert") as batch_op:
        batch_op.add_column(sa.Column('always_chat', sa.Boolean(), server_default='f', nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("group_alert") as batch_op:
        batch_op.drop_column('chat_message')
        batch_op.drop_column('always_chat')
    # ### end Alembic commands ###
