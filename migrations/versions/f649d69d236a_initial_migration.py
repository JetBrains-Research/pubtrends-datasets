"""Initial migration.

Revision ID: f649d69d236a
Revises: 
Create Date: 2026-01-20 14:06:35.493583

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f649d69d236a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('gse_update',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date', sa.DateTime(), nullable=True),
    sa.Column('completed', sa.Boolean(), nullable=True),
    sa.Column('last_update_date_start', sa.DateTime(), nullable=True),
    sa.Column('last_update_date_end', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id', name='pk_gse_update_id')
    )
    with op.batch_alter_table('gse_update', schema=None) as batch_op:
        batch_op.create_index('gse_update_id_idx', ['id'], unique=False)

    op.create_table('gse_update_association',
    sa.Column('update_id', sa.Integer(), nullable=False),
    sa.Column('gse_acc', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['update_id'], ['gse_update.id'], ),
    sa.PrimaryKeyConstraint('update_id', 'gse_acc')
    )
    with op.batch_alter_table('gse', schema=None) as batch_op:
        batch_op.alter_column('gse',
               existing_type=sa.TEXT(),
               nullable=False)

    # ### end Alembic commands ###


def downgrade():
    with op.batch_alter_table('gse', schema=None) as batch_op:
        batch_op.alter_column('gse',
               existing_type=sa.TEXT(),
               nullable=True)


    op.drop_table('gse_update_association')
    with op.batch_alter_table('gse_update', schema=None) as batch_op:
        batch_op.drop_index('gse_update_id_idx')

    op.drop_table('gse_update')
    # ### end Alembic commands ###
