"""adding group alert to counts

Revision ID: c4157102f944
Revises: c7acc817b580
Create Date: 2019-04-16 21:12:32.369515

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4157102f944'
down_revision = 'c7acc817b580'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('count', sa.Column('group_name', sa.Text(), nullable=True))
    with op.batch_alter_table("count") as batch_op:
        batch_op.create_foreign_key('group_alert_count_fk', 'group_alert', ['group_name'], ['group_name'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('group_alert_count_fk', 'count', type_='foreignkey')
    op.drop_column('count', 'group_name')
    # ### end Alembic commands ###
