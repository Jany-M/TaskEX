from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship

from db.db_setup import Base


class ResourceType(Base):
    """
    Represents one of the four Evony resource tile types.
    Seeded automatically on init_db(); tile templates are uploaded by the user
    via the Resource Tile Manager (Configure Resource Tile Templates).
    """
    __tablename__ = 'resource_types'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)       # Food, Lumber, Stone, Ore
    preview_image = Column(String, nullable=True)
    color_hint = Column(String, nullable=True)  # "R,G,B" hint for map detection fallback

    tile_templates = relationship(
        'ResourceTileTemplate',
        back_populates='resource_type',
        cascade='all, delete-orphan'
    )


class ResourceTileTemplate(Base):
    """
    One tile-level image template for a resource type (e.g. Food lv18).
    Multiple levels per resource type are supported.
    """
    __tablename__ = 'resource_tile_templates'

    id = Column(Integer, primary_key=True)
    resource_type_id = Column(Integer, ForeignKey('resource_types.id'), nullable=False)
    tile_level = Column(Integer, nullable=False)   # e.g. 16, 17, 18
    img_540p = Column(String, nullable=True)
    img_threshold = Column(Float, nullable=False, default=0.85)
    preview_image = Column(String, nullable=True)

    resource_type = relationship('ResourceType', back_populates='tile_templates')


class GatherPresetConfiguration(Base):
    """
    Profile-scoped container for gather preset slots.
    One configuration per profile (created lazily on first access).
    """
    __tablename__ = 'gather_preset_configurations'

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False)

    profile = relationship('Profile')
    options = relationship(
        'GatherPresetOption',
        back_populates='configuration',
        cascade='all, delete-orphan'
    )


class GatherPresetOption(Base):
    """
    One gather march preset slot (1–4): general selection + troop config.
    """
    __tablename__ = 'gather_preset_options'

    id = Column(Integer, primary_key=True)
    gather_preset_configuration_id = Column(
        Integer,
        ForeignKey('gather_preset_configurations.id', ondelete='CASCADE'),
        nullable=False
    )
    preset_number = Column(Integer, nullable=False)       # 1-4
    general_id = Column(Integer, ForeignKey('generals.id'), nullable=True)
    troop_config = Column(JSON, nullable=True)             # {infantry:0, mounted:5000, ...}

    configuration = relationship('GatherPresetConfiguration', back_populates='options')
