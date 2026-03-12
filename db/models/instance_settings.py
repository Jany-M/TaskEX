from sqlalchemy import Column, Integer, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship

from db.db_setup import Base


class InstanceSettings(Base):
    """Instance-scoped runtime settings that must never be shared across profiles."""
    __tablename__ = "instance_settings"

    id = Column(Integer, primary_key=True)
    instance_id = Column(Integer, ForeignKey("instances.id", ondelete="CASCADE"), nullable=False)
    auto_bubble = Column(JSON, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("instance_id", name="uq_instance_settings_instance_id"),
    )

    instance = relationship("Instance", back_populates="settings")
