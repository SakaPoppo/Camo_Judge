"""Migration, schema, defaults, trigger, and seed integration tests."""

from sqlalchemy import func, inspect, select, update

from camo_judge.models import BackgroundType, CamouflagePattern, Image
from camo_judge.seed import seed_master_data


def test_migration_creates_exact_core_tables_and_columns(engine) -> None:
    inspector = inspect(engine)
    expected_columns = {
        "camouflage_patterns": {
            "id",
            "code",
            "name",
            "family",
            "comparison_group",
            "created_at",
        },
        "background_types": {"id", "code", "name", "description", "created_at"},
        "images": {
            "id",
            "code",
            "role",
            "camouflage_pattern_id",
            "background_type_id",
            "vegetation_state",
            "source_type",
            "source_url",
            "license",
            "publication_status",
            "quality_status",
            "quality_reason",
            "capture_date",
            "distance_m",
            "camera_height_m",
            "created_at",
            "lighting",
            "notes",
            "updated_at",
        },
        "image_files": {
            "id",
            "image_id",
            "file_type",
            "storage_path",
            "file_format",
            "width_px",
            "height_px",
            "color_space",
            "file_hash",
            "processing_version",
            "created_at",
        },
    }

    assert set(expected_columns).issubset(inspector.get_table_names())
    for table_name, columns in expected_columns.items():
        actual_columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        assert actual_columns == columns


def test_seed_registers_all_masters_and_is_idempotent(session) -> None:
    seed_master_data(session)
    session.commit()
    seed_master_data(session)
    session.commit()

    assert session.scalar(select(func.count(CamouflagePattern.id))) == 9
    assert session.scalar(select(func.count(BackgroundType.id))) == 6
    camouflage_rows = session.execute(
        select(
            CamouflagePattern.code,
            CamouflagePattern.name,
            CamouflagePattern.comparison_group,
        )
    ).all()
    assert {row.code: (row.name, row.comparison_group) for row in camouflage_rows} == {
        "CM01": ("MultiCam Tropic", "green"),
        "CM02": ("MultiCam Original", "general"),
        "CM03": ("A-TACS FG", "green"),
        "CM04": ("A-TACS AU", "dry"),
        "CM05": ("Tiger Stripe（緑系）", "green"),
        "CM06": ("Desert Tiger Stripe", "dry"),
        "CM07": ("陸上自衛隊迷彩2型", "independent"),
        "CM08": ("OD（単色）", "solid"),
        "CM09": ("PenCott GreenZone", "green"),
    }
    background_rows = session.execute(
        select(BackgroundType.code, BackgroundType.name)
    ).all()
    assert {row.code: row.name for row in background_rows} == {
        "BG01": "笹・ササ藪",
        "BG02": "低木・灌木の茂み",
        "BG03": "高草・ススキ",
        "BG04": "シダ・低い下草",
        "BG05": "木の根元・樹幹",
        "BG06": "ツル植物・絡み合った藪",
    }


def test_image_defaults_and_updated_at_trigger(session) -> None:
    seed_master_data(session)
    background_id = session.scalar(
        select(BackgroundType.id).where(BackgroundType.code == "BG01")
    )
    image = Image(
        code="IMG0001",
        role="background",
        background_type_id=background_id,
        vegetation_state="green",
        source_type="self",
    )
    session.add(image)
    session.commit()
    session.refresh(image)

    assert image.quality_status == "pending"
    assert image.publication_status == "unknown"
    original_updated_at = image.updated_at

    session.execute(
        update(Image).where(Image.id == image.id).values(notes="updated by test")
    )
    session.commit()
    session.refresh(image)

    assert image.updated_at > original_updated_at
