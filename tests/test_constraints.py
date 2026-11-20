"""Database constraint integration tests."""

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from camo_judge.models import BackgroundType, CamouflagePattern, Image, ImageFile
from camo_judge.seed import seed_master_data


def _master_ids(session) -> tuple[int, int]:
    seed_master_data(session)
    session.commit()
    camouflage_id = session.scalar(
        select(CamouflagePattern.id).where(CamouflagePattern.code == "CM01")
    )
    background_id = session.scalar(
        select(BackgroundType.id).where(BackgroundType.code == "BG01")
    )
    return camouflage_id, background_id


def _background_image(background_id: int, **overrides) -> Image:
    values = {
        "code": "IMG0001",
        "role": "background",
        "background_type_id": background_id,
        "vegetation_state": "green",
        "source_type": "self",
    }
    values.update(overrides)
    return Image(**values)


def _assert_commit_fails(session) -> None:
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_image_code_is_unique(session) -> None:
    _, background_id = _master_ids(session)
    session.add(_background_image(background_id))
    session.commit()
    session.add(_background_image(background_id, vegetation_state="dry"))
    _assert_commit_fails(session)


def test_image_foreign_key_is_enforced(session) -> None:
    _master_ids(session)
    session.add(_background_image(999_999))
    _assert_commit_fails(session)


@pytest.mark.parametrize(
    "values",
    [
        {
            "role": "background",
            "background_type_id": None,
            "vegetation_state": "green",
        },
        {
            "role": "background",
            "camouflage_pattern_id": "use_master",
            "vegetation_state": "green",
        },
        {
            "role": "camouflage",
            "background_type_id": None,
            "camouflage_pattern_id": "use_master",
            "vegetation_state": "green",
        },
    ],
)
def test_background_and_camouflage_classification_is_exclusive(session, values) -> None:
    camouflage_id, background_id = _master_ids(session)
    resolved_values = {
        key: camouflage_id if value == "use_master" else value
        for key, value in values.items()
    }
    session.add(_background_image(background_id, **resolved_values))
    _assert_commit_fails(session)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("quality_status", "approved"),
        ("publication_status", "published"),
        ("source_type", "unknown"),
    ],
)
def test_status_and_source_checks_reject_unknown_values(
    session, field, invalid_value
) -> None:
    _, background_id = _master_ids(session)
    session.add(_background_image(background_id, **{field: invalid_value}))
    _assert_commit_fails(session)


def test_rejected_image_requires_a_reason(session) -> None:
    _, background_id = _master_ids(session)
    session.add(
        _background_image(
            background_id,
            quality_status="rejected",
            quality_reason="   ",
        )
    )
    _assert_commit_fails(session)


def test_allowed_public_image_requires_source_and_license(session) -> None:
    _, background_id = _master_ids(session)
    session.add(
        _background_image(
            background_id,
            source_type="public",
            publication_status="allowed",
        )
    )
    _assert_commit_fails(session)


@pytest.mark.parametrize(
    "measurement", [{"distance_m": Decimal("0")}, {"camera_height_m": Decimal("-1")}]
)
def test_measurements_must_be_positive_when_present(session, measurement) -> None:
    _, background_id = _master_ids(session)
    session.add(_background_image(background_id, **measurement))
    _assert_commit_fails(session)


def test_one_raw_file_and_multiple_processed_versions_are_supported(session) -> None:
    _, background_id = _master_ids(session)
    image = _background_image(background_id)
    session.add(image)
    session.commit()

    session.add(
        ImageFile(
            image_id=image.id,
            file_type="raw",
            storage_path="data/raw/IMG0001.jpg",
            file_format="JPEG",
            width_px=2048,
            height_px=1536,
            color_space="sRGB",
            file_hash="a" * 64,
        )
    )
    session.commit()

    session.add_all(
        [
            ImageFile(
                image_id=image.id,
                file_type="processed",
                storage_path=f"data/processed/IMG0001_{version}.png",
                file_format="PNG",
                width_px=1024,
                height_px=768,
                color_space="sRGB",
                file_hash=hash_character * 64,
                processing_version=version,
            )
            for version, hash_character in (("v1", "b"), ("v2", "c"))
        ]
    )
    session.commit()

    assert len(image.files) == 3

    session.add(
        ImageFile(
            image_id=image.id,
            file_type="raw",
            storage_path="data/raw/IMG0001-duplicate.jpg",
            file_format="JPEG",
            width_px=2048,
            height_px=1536,
            file_hash="d" * 64,
        )
    )
    _assert_commit_fails(session)

    session.add(
        ImageFile(
            image_id=image.id,
            file_type="processed",
            storage_path="data/processed/IMG0001_v1_duplicate.png",
            file_format="PNG",
            width_px=1024,
            height_px=768,
            file_hash="e" * 64,
            processing_version="v1",
        )
    )
    _assert_commit_fails(session)


@pytest.mark.parametrize(
    "values",
    [
        {"file_type": "original", "processing_version": None},
        {"file_type": "raw", "processing_version": "v1"},
        {"file_type": "processed", "processing_version": None},
        {"file_type": "raw", "processing_version": None, "storage_path": "/tmp/raw.jpg"},
        {"file_type": "raw", "processing_version": None, "storage_path": "C:\\raw.jpg"},
        {"file_type": "raw", "processing_version": None, "storage_path": "data/../raw.jpg"},
    ],
)
def test_image_file_checks_reject_invalid_metadata(session, values) -> None:
    _, background_id = _master_ids(session)
    image = _background_image(background_id)
    session.add(image)
    session.commit()

    defaults = {
        "image_id": image.id,
        "file_type": "raw",
        "storage_path": "data/raw/IMG0001.jpg",
        "file_format": "JPEG",
        "width_px": 1024,
        "height_px": 768,
        "file_hash": "f" * 64,
        "processing_version": None,
    }
    defaults.update(values)
    session.add(ImageFile(**defaults))
    _assert_commit_fails(session)
