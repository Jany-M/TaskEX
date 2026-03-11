from sqlalchemy import Column, Integer, String, Float

from db.db_setup import Base


class BubbleType(Base):
    """
    Represents one of the four Evony protection bubble types.
    Seeded automatically on init_db(); templates are uploaded by the user
    via the Bubble Manager panel (Configure Bubble Templates).
    """
    __tablename__ = 'bubble_types'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)             # "8h", "24h", "3 Days", "7 Days"
    duration_hours = Column(Integer, nullable=False)  # 8, 24, 72, 168
    img_540p = Column(String, nullable=True)          # path relative to project root
    preview_image = Column(String, nullable=True)
    img_threshold = Column(Float, nullable=False, default=0.85)
