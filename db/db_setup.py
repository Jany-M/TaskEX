from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import sys
from config.settings import DATABASE_URL
from db.migration import migrate_database_with_backup

# Base class for the models
Base = declarative_base()

# Create the SQLite engine
engine = create_engine(DATABASE_URL)

# Create a session factory
Session = sessionmaker(bind=engine)

# Initialize the session
def get_session():
    return Session()

# Initialize database (create tables)
def _seed_bubble_types(session):
    from db.models.bubble import BubbleType
    if session.query(BubbleType).count() == 0:
        defaults = [
            BubbleType(id=1, name="8h",     duration_hours=8,   img_threshold=0.85),
            BubbleType(id=2, name="24h",    duration_hours=24,  img_threshold=0.85),
            BubbleType(id=3, name="3 Days", duration_hours=72,  img_threshold=0.85),
            BubbleType(id=4, name="7 Days", duration_hours=168, img_threshold=0.85),
        ]
        session.add_all(defaults)
        session.commit()


def _seed_resource_types(session):
    from db.models.resource_tile import ResourceType
    if session.query(ResourceType).count() == 0:
        defaults = [
            ResourceType(id=1, name="Food",   color_hint="255,220,100"),
            ResourceType(id=2, name="Lumber", color_hint="100,180,50"),
            ResourceType(id=3, name="Stone",  color_hint="190,190,190"),
            ResourceType(id=4, name="Ore",    color_hint="80,80,120"),
        ]
        session.add_all(defaults)
        session.commit()


def _seed_monster_categories_and_logics(session):
    """Ensure default monster categories and logics exist."""
    from db.models import MonsterCategory, MonsterLogic
    
    # Seed default categories if none exist
    category_ids = {row_id for (row_id,) in session.query(MonsterCategory.id).all()}
    if not any(cid in category_ids for cid in [1, 2, 3, 4]):
        defaults = [
            MonsterCategory(id=1, name="Barbarian"),
            MonsterCategory(id=2, name="Ranger"),
            MonsterCategory(id=3, name="Mage"),
            MonsterCategory(id=4, name="Warrior"),
        ]
        for cat in defaults:
            if cat.id not in category_ids:
                session.add(cat)
        session.commit()
    
    # Seed default logics if none exist
    logic_ids = {row_id for (row_id,) in session.query(MonsterLogic.id).all()}
    if not any(lid in logic_ids for lid in [1, 2, 3, 4]):
        defaults = [
            MonsterLogic(id=1, logic="Single-Level Boss", description="Unique Name, Power, and Level"),
            MonsterLogic(id=2, logic="Multi-Level Boss", description="Same Name, Different Power and Level"),
            MonsterLogic(id=3, logic="Variant-Level Boss", description="Different Name, Different Power, and Level"),
            MonsterLogic(id=4, logic="Custom-Level Boss", description="Same Name, Multiple Variants and Levels."),
        ]
        for logic in defaults:
            if logic.id not in logic_ids:
                session.add(logic)
        session.commit()


def _seed_monsters_from_bundled_db(session):
    from db.models import MonsterCategory, MonsterLogic, MonsterImage, BossMonster, MonsterLevel

    if session.query(BossMonster).count() > 0:
        return

    active_db_path = Path(engine.url.database).resolve()

    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
        candidates = [
            base_dir / "_internal" / "db" / "task_ex.db",
            Path(getattr(sys, "_MEIPASS", "")) / "db" / "task_ex.db",
            base_dir / "db" / "task_ex.db",
        ]
        bundled_db_path = next((p for p in candidates if p.exists()), None)
    else:
        bundled_db_path = Path(__file__).resolve().parent / "task_ex.db"

    if bundled_db_path is None or not bundled_db_path.exists():
        return

    if bundled_db_path.resolve() == active_db_path:
        return

    seed_engine = create_engine(f"sqlite:///{bundled_db_path}")
    SeedSession = sessionmaker(bind=seed_engine)
    seed_session = SeedSession()

    try:
        if seed_session.query(BossMonster).count() == 0:
            return

        existing_category_ids = {row_id for (row_id,) in session.query(MonsterCategory.id).all()}
        for row in seed_session.query(MonsterCategory).all():
            if row.id not in existing_category_ids:
                session.add(MonsterCategory(id=row.id, name=row.name))

        existing_logic_ids = {row_id for (row_id,) in session.query(MonsterLogic.id).all()}
        for row in seed_session.query(MonsterLogic).all():
            if row.id not in existing_logic_ids:
                session.add(MonsterLogic(id=row.id, logic=row.logic, description=row.description))

        existing_image_ids = {row_id for (row_id,) in session.query(MonsterImage.id).all()}
        for row in seed_session.query(MonsterImage).all():
            if row.id not in existing_image_ids:
                session.add(MonsterImage(
                    id=row.id,
                    preview_image=row.preview_image,
                    img_540p=row.img_540p,
                    img_threshold=row.img_threshold,
                    click_pos=row.click_pos,
                ))

        existing_boss_ids = {row_id for (row_id,) in session.query(BossMonster.id).all()}
        for row in seed_session.query(BossMonster).all():
            if row.id not in existing_boss_ids:
                session.add(BossMonster(
                    id=row.id,
                    preview_name=row.preview_name,
                    monster_category_id=row.monster_category_id,
                    monster_image_id=row.monster_image_id,
                    monster_logic_id=row.monster_logic_id,
                    enable_map_scan=row.enable_map_scan,
                    system=row.system,
                ))

        existing_level_ids = {row_id for (row_id,) in session.query(MonsterLevel.id).all()}
        for row in seed_session.query(MonsterLevel).all():
            if row.id not in existing_level_ids:
                session.add(MonsterLevel(
                    id=row.id,
                    boss_monster_id=row.boss_monster_id,
                    level=row.level,
                    name=row.name,
                    power=row.power,
                ))

        session.commit()
    finally:
        seed_session.close()
        seed_engine.dispose()


def init_db():
    from db.models import General  # Import models triggers all metadata registration
    migrate_database_with_backup()
    Base.metadata.create_all(engine)
    session = Session()
    try:
        _seed_bubble_types(session)
        _seed_resource_types(session)
        _seed_monster_categories_and_logics(session)
        _seed_monsters_from_bundled_db(session)
    finally:
        session.close()
