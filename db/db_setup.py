from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.settings import DATABASE_URL

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


def init_db():
    from db.models import General  # Import models triggers all metadata registration
    Base.metadata.create_all(engine)
    session = Session()
    try:
        _seed_bubble_types(session)
        _seed_resource_types(session)
    finally:
        session.close()
