"""Idempotent seed data for camouflage and background masters."""

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from camo_judge.db import get_engine
from camo_judge.models import BackgroundType, CamouflagePattern


CAMOUFLAGE_PATTERNS = (
    {
        "code": "CM01",
        "name": "MultiCam Tropic",
        "family": "MultiCam",
        "comparison_group": "green",
    },
    {
        "code": "CM02",
        "name": "MultiCam Original",
        "family": "MultiCam",
        "comparison_group": "general",
    },
    {
        "code": "CM03",
        "name": "A-TACS FG",
        "family": "A-TACS",
        "comparison_group": "green",
    },
    {
        "code": "CM04",
        "name": "A-TACS AU",
        "family": "A-TACS",
        "comparison_group": "dry",
    },
    {
        "code": "CM05",
        "name": "Tiger Stripe（緑系）",
        "family": "Tiger Stripe",
        "comparison_group": "green",
    },
    {
        "code": "CM06",
        "name": "Desert Tiger Stripe",
        "family": "Tiger Stripe",
        "comparison_group": "dry",
    },
    {
        "code": "CM07",
        "name": "陸上自衛隊迷彩2型",
        "family": "JGSDF",
        "comparison_group": "independent",
    },
    {
        "code": "CM08",
        "name": "OD（単色）",
        "family": None,
        "comparison_group": "solid",
    },
    {
        "code": "CM09",
        "name": "PenCott GreenZone",
        "family": "PenCott",
        "comparison_group": "green",
    },
)

BACKGROUND_TYPES = (
    {"code": "BG01", "name": "笹・ササ藪", "description": None},
    {"code": "BG02", "name": "低木・灌木の茂み", "description": None},
    {"code": "BG03", "name": "高草・ススキ", "description": None},
    {"code": "BG04", "name": "シダ・低い下草", "description": None},
    {"code": "BG05", "name": "木の根元・樹幹", "description": None},
    {"code": "BG06", "name": "ツル植物・絡み合った藪", "description": None},
)


def seed_master_data(session: Session) -> None:
    """Insert or update fixed masters by code without creating duplicates."""
    camouflage_statement = insert(CamouflagePattern).values(CAMOUFLAGE_PATTERNS)
    session.execute(
        camouflage_statement.on_conflict_do_update(
            index_elements=[CamouflagePattern.code],
            set_={
                "name": camouflage_statement.excluded.name,
                "family": camouflage_statement.excluded.family,
                "comparison_group": camouflage_statement.excluded.comparison_group,
            },
        )
    )

    background_statement = insert(BackgroundType).values(BACKGROUND_TYPES)
    session.execute(
        background_statement.on_conflict_do_update(
            index_elements=[BackgroundType.code],
            set_={
                "name": background_statement.excluded.name,
                "description": background_statement.excluded.description,
            },
        )
    )


def main() -> None:
    with Session(get_engine()) as session:
        seed_master_data(session)
        session.commit()
        camouflage_count = session.scalar(select(func.count(CamouflagePattern.id)))
        background_count = session.scalar(select(func.count(BackgroundType.id)))

    print(f"Seed complete: camouflage_patterns={camouflage_count}, background_types={background_count}")


if __name__ == "__main__":
    main()
