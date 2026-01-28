"""Rename geometadb update job tables for increased clarity

Revision ID: 0d34a4938fe5
Revises: 465aed4fb5e2
Create Date: 2026-01-27 12:21:37.880553

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '0d34a4938fe5'
down_revision = '465aed4fb5e2'
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table("gse_update", "geometadb_update_job")
    with op.batch_alter_table("geometadb_update_job", schema=None) as batch_op:
        batch_op.drop_index("gse_update_id_idx")
        batch_op.create_index(batch_op.f("geometadb_update_job_id_idx"), ["id"], unique=False)

    op.rename_table("gse_update_association", "gse_update")
    with op.batch_alter_table("gse_update", schema=None) as batch_op:
        batch_op.alter_column("update_id", new_column_name="geometadb_update_job_id")



def downgrade():
    with op.batch_alter_table("gse_update", schema=None) as batch_op:
        batch_op.alter_column("geometadb_update_job_id", new_column_name="update_id")
    op.rename_table("gse_update", "gse_update_association")

    with op.batch_alter_table("geometadb_update_job", schema=None) as batch_op:
        batch_op.drop_index("geometadb_update_job_id_idx")
        batch_op.create_index(batch_op.f("gse_update_id_idx"), ["id"], unique=False)
    op.rename_table("geometadb_update_job", "gse_update")
