"""Add indexes for plant-related tables

Revision ID: add_indexes_to_plant_tables
Revises: 58923d25f066
Create Date: 2025-10-14
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "add_indexes_to_plant_tables"
down_revision = "58923d25f066"
branch_labels = None
depends_on = None


def upgrade():
    # --- plants ---
    op.create_index(
        "idx_plants_breeder_id",
        "plants",
        ["breeder_id"],
    )

    # --- plant_measurements ---
    op.create_index(
        "idx_measurements_plant_id",
        "plant_measurements",
        ["plant_id"],
    )
    op.create_index(
        "idx_measurements_date",
        "plant_measurements",
        ["date"],
    )

    # --- plant_fruits ---
    op.create_index(
        "idx_fruits_measurement_id",
        "plant_fruits",
        ["measurement_id"],
    )

    # --- plant_files ---
    op.create_index(
        "idx_files_plant_id",
        "plant_files",
        ["plant_id"],
    )
    op.create_index(
        "idx_files_status",
        "plant_files",
        ["status"],
    )


def downgrade():
    # --- plant_files ---
    op.drop_index("idx_files_status", table_name="plant_files")
    op.drop_index("idx_files_plant_id", table_name="plant_files")

    # --- plant_fruits ---
    op.drop_index("idx_fruits_measurement_id", table_name="plant_fruits")

    # --- plant_measurements ---
    op.drop_index("idx_measurements_date", table_name="plant_measurements")
    op.drop_index("idx_measurements_plant_id", table_name="plant_measurements")

    # --- plants ---
    op.drop_index("idx_plants_breeder_id", table_name="plants")
