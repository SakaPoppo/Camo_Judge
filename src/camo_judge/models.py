"""Core relational models. The first schema revision is maintained by Alembic."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class CamouflagePattern(Base):
    __tablename__ = "camouflage_patterns"
    __table_args__ = (
        CheckConstraint("code ~ '^CM[0-9]{2}$'", name="ck_camouflage_code_format"),
        CheckConstraint(
            "comparison_group IN ('green','dry','general','independent','solid')",
            name="ck_camouflage_group",
        ),
        CheckConstraint("length(btrim(name)) > 0", name="ck_camouflage_name_not_blank"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    code: Mapped[str] = mapped_column(String(4), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    family: Mapped[str | None] = mapped_column(String(50))
    comparison_group: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    images: Mapped[list["Image"]] = relationship(back_populates="camouflage_pattern")


class BackgroundType(Base):
    __tablename__ = "background_types"
    __table_args__ = (
        CheckConstraint("code ~ '^BG[0-9]{2}$'", name="ck_background_code_format"),
        CheckConstraint("length(btrim(name)) > 0", name="ck_background_name_not_blank"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    code: Mapped[str] = mapped_column(String(4), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    images: Mapped[list["Image"]] = relationship(back_populates="background_type")


class Image(Base):
    __tablename__ = "images"
    __table_args__ = (
        CheckConstraint("code ~ '^IMG[0-9]{4,}$'", name="ck_image_code_format"),
        CheckConstraint("role IN ('background','camouflage')", name="ck_image_role"),
        CheckConstraint(
            "(role = 'background' AND background_type_id IS NOT NULL AND "
            "camouflage_pattern_id IS NULL AND vegetation_state IN ('green','dry')) "
            "OR (role = 'camouflage' AND camouflage_pattern_id IS NOT NULL AND "
            "background_type_id IS NULL AND vegetation_state IS NULL)",
            name="ck_image_role_keys",
        ),
        CheckConstraint("source_type IN ('self','public')", name="ck_image_source_type"),
        CheckConstraint(
            "publication_status IN ('unknown','allowed','not_allowed')",
            name="ck_image_publication_status",
        ),
        CheckConstraint(
            "quality_status IN ('accepted','pending','rejected')",
            name="ck_image_quality_status",
        ),
        CheckConstraint(
            "distance_m IS NULL OR distance_m > 0",
            name="ck_image_distance_positive",
        ),
        CheckConstraint(
            "camera_height_m IS NULL OR camera_height_m > 0",
            name="ck_image_camera_height_positive",
        ),
        CheckConstraint(
            "quality_status <> 'rejected' OR NULLIF(btrim(quality_reason), '') IS NOT NULL",
            name="ck_image_rejection_reason",
        ),
        CheckConstraint(
            "source_type <> 'public' OR publication_status <> 'allowed' OR "
            "(NULLIF(btrim(source_url), '') IS NOT NULL AND "
            "NULLIF(btrim(license), '') IS NOT NULL)",
            name="ck_image_public_rights",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    camouflage_pattern_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("camouflage_patterns.id", ondelete="RESTRICT"),
        index=True,
    )
    background_type_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("background_types.id", ondelete="RESTRICT"),
        index=True,
    )
    vegetation_state: Mapped[str | None] = mapped_column(String(10))
    source_type: Mapped[str] = mapped_column(String(10), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    license: Mapped[str | None] = mapped_column(Text)
    publication_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'unknown'")
    )
    quality_status: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default=text("'pending'")
    )
    quality_reason: Mapped[str | None] = mapped_column(Text)
    capture_date: Mapped[date | None] = mapped_column(Date)
    distance_m: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    camera_height_m: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    lighting: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    camouflage_pattern: Mapped[CamouflagePattern | None] = relationship(back_populates="images")
    background_type: Mapped[BackgroundType | None] = relationship(back_populates="images")
    files: Mapped[list["ImageFile"]] = relationship(back_populates="image")


class ImageFile(Base):
    __tablename__ = "image_files"
    __table_args__ = (
        CheckConstraint("file_type IN ('raw','processed')", name="ck_image_file_type"),
        CheckConstraint("file_format IN ('JPEG','PNG')", name="ck_image_file_format"),
        CheckConstraint("width_px > 0 AND height_px > 0", name="ck_image_file_dimensions"),
        CheckConstraint("file_hash ~ '^[0-9a-f]{64}$'", name="ck_image_file_sha256"),
        CheckConstraint(
            "(file_type = 'raw' AND processing_version IS NULL) "
            "OR (file_type = 'processed' AND NULLIF(btrim(processing_version), '') IS NOT NULL)",
            name="ck_image_file_processing_version",
        ),
        CheckConstraint(
            "length(btrim(storage_path)) > 0 AND "
            "storage_path !~ '(^/|^[A-Za-z]:[\\\\/]|(^|/)\\.\\.(/|$))'",
            name="ck_image_file_relative_path",
        ),
        Index(
            "uq_image_files_one_raw_per_image",
            "image_id",
            unique=True,
            postgresql_where=text("file_type = 'raw'"),
        ),
        Index(
            "uq_image_files_processed_version",
            "image_id",
            "processing_version",
            unique=True,
            postgresql_where=text("file_type = 'processed'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    image_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("images.id", ondelete="RESTRICT"), nullable=False
    )
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    file_format: Mapped[str] = mapped_column(String(4), nullable=False)
    width_px: Mapped[int] = mapped_column(BigInteger, nullable=False)
    height_px: Mapped[int] = mapped_column(BigInteger, nullable=False)
    color_space: Mapped[str | None] = mapped_column(String(40))
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    processing_version: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    image: Mapped[Image] = relationship(back_populates="files")
