"""Create the four core image metadata tables.

Revision ID: 0001
Revises:
Create Date: 2026-11-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "camouflage_patterns",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("code", sa.String(length=4), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("family", sa.String(length=50), nullable=True),
        sa.Column("comparison_group", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("code ~ '^CM[0-9]{2}$'", name="ck_camouflage_code_format"),
        sa.CheckConstraint(
            "comparison_group IN ('green','dry','general','independent','solid')",
            name="ck_camouflage_group",
        ),
        sa.CheckConstraint(
            "length(btrim(name)) > 0", name="ck_camouflage_name_not_blank"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "background_types",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("code", sa.String(length=4), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("code ~ '^BG[0-9]{2}$'", name="ck_background_code_format"),
        sa.CheckConstraint(
            "length(btrim(name)) > 0", name="ck_background_name_not_blank"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "images",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("role", sa.String(length=10), nullable=False),
        sa.Column("camouflage_pattern_id", sa.BigInteger(), nullable=True),
        sa.Column("background_type_id", sa.BigInteger(), nullable=True),
        sa.Column("vegetation_state", sa.String(length=10), nullable=True),
        sa.Column("source_type", sa.String(length=10), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("license", sa.Text(), nullable=True),
        sa.Column(
            "publication_status",
            sa.String(length=20),
            server_default=sa.text("'unknown'"),
            nullable=False,
        ),
        sa.Column(
            "quality_status",
            sa.String(length=10),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("quality_reason", sa.Text(), nullable=True),
        sa.Column("capture_date", sa.Date(), nullable=True),
        sa.Column("distance_m", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("camera_height_m", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("lighting", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("code ~ '^IMG[0-9]{4,}$'", name="ck_image_code_format"),
        sa.CheckConstraint(
            "role IN ('background','camouflage')", name="ck_image_role"
        ),
        sa.CheckConstraint(
            "(role = 'background' AND background_type_id IS NOT NULL AND "
            "camouflage_pattern_id IS NULL AND vegetation_state IN ('green','dry')) "
            "OR (role = 'camouflage' AND camouflage_pattern_id IS NOT NULL AND "
            "background_type_id IS NULL AND vegetation_state IS NULL)",
            name="ck_image_role_keys",
        ),
        sa.CheckConstraint(
            "source_type IN ('self','public')", name="ck_image_source_type"
        ),
        sa.CheckConstraint(
            "publication_status IN ('unknown','allowed','not_allowed')",
            name="ck_image_publication_status",
        ),
        sa.CheckConstraint(
            "quality_status IN ('accepted','pending','rejected')",
            name="ck_image_quality_status",
        ),
        sa.CheckConstraint(
            "distance_m IS NULL OR distance_m > 0",
            name="ck_image_distance_positive",
        ),
        sa.CheckConstraint(
            "camera_height_m IS NULL OR camera_height_m > 0",
            name="ck_image_camera_height_positive",
        ),
        sa.CheckConstraint(
            "quality_status <> 'rejected' OR "
            "NULLIF(btrim(quality_reason), '') IS NOT NULL",
            name="ck_image_rejection_reason",
        ),
        sa.CheckConstraint(
            "source_type <> 'public' OR publication_status <> 'allowed' OR "
            "(NULLIF(btrim(source_url), '') IS NOT NULL AND "
            "NULLIF(btrim(license), '') IS NOT NULL)",
            name="ck_image_public_rights",
        ),
        sa.ForeignKeyConstraint(
            ["background_type_id"],
            ["background_types.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["camouflage_pattern_id"],
            ["camouflage_patterns.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(
        op.f("ix_images_background_type_id"),
        "images",
        ["background_type_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_images_camouflage_pattern_id"),
        "images",
        ["camouflage_pattern_id"],
        unique=False,
    )

    op.execute(
        """
        CREATE FUNCTION set_images_updated_at()
        RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = clock_timestamp();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_images_updated_at
        BEFORE UPDATE ON images
        FOR EACH ROW EXECUTE FUNCTION set_images_updated_at()
        """
    )

    op.create_table(
        "image_files",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("image_id", sa.BigInteger(), nullable=False),
        sa.Column("file_type", sa.String(length=10), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("file_format", sa.String(length=4), nullable=False),
        sa.Column("width_px", sa.BigInteger(), nullable=False),
        sa.Column("height_px", sa.BigInteger(), nullable=False),
        sa.Column("color_space", sa.String(length=40), nullable=True),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("processing_version", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "file_type IN ('raw','processed')", name="ck_image_file_type"
        ),
        sa.CheckConstraint(
            "file_format IN ('JPEG','PNG')", name="ck_image_file_format"
        ),
        sa.CheckConstraint(
            "width_px > 0 AND height_px > 0", name="ck_image_file_dimensions"
        ),
        sa.CheckConstraint(
            "file_hash ~ '^[0-9a-f]{64}$'", name="ck_image_file_sha256"
        ),
        sa.CheckConstraint(
            "(file_type = 'raw' AND processing_version IS NULL) "
            "OR (file_type = 'processed' AND "
            "NULLIF(btrim(processing_version), '') IS NOT NULL)",
            name="ck_image_file_processing_version",
        ),
        sa.CheckConstraint(
            "length(btrim(storage_path)) > 0 AND "
            "storage_path !~ '(^/|^[A-Za-z]:[\\\\/]|(^|/)\\.\\.(/|$))'",
            name="ck_image_file_relative_path",
        ),
        sa.ForeignKeyConstraint(
            ["image_id"], ["images.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path"),
    )
    op.create_index(
        "uq_image_files_one_raw_per_image",
        "image_files",
        ["image_id"],
        unique=True,
        postgresql_where=sa.text("file_type = 'raw'"),
    )
    op.create_index(
        "uq_image_files_processed_version",
        "image_files",
        ["image_id", "processing_version"],
        unique=True,
        postgresql_where=sa.text("file_type = 'processed'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_image_files_processed_version",
        table_name="image_files",
        postgresql_where=sa.text("file_type = 'processed'"),
    )
    op.drop_index(
        "uq_image_files_one_raw_per_image",
        table_name="image_files",
        postgresql_where=sa.text("file_type = 'raw'"),
    )
    op.drop_table("image_files")
    op.execute("DROP TRIGGER trg_images_updated_at ON images")
    op.execute("DROP FUNCTION set_images_updated_at()")
    op.drop_index(op.f("ix_images_camouflage_pattern_id"), table_name="images")
    op.drop_index(op.f("ix_images_background_type_id"), table_name="images")
    op.drop_table("images")
    op.drop_table("background_types")
    op.drop_table("camouflage_patterns")
