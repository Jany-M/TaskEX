from db.db_setup import get_session
from db.models import ResourceType, ResourceTileTemplate


def get_all_resource_types():
    """Return all four seeded resource types ordered by id."""
    session = get_session()
    try:
        return session.query(ResourceType).order_by(ResourceType.id).all()
    finally:
        session.close()


def get_tile_templates_for_resource(resource_type_id, min_level=None, max_level=None):
    """
    Return tile templates for a resource type, optionally filtered by level range.
    Results are ordered highest level first (preferred for dispatching).
    """
    session = get_session()
    try:
        q = session.query(ResourceTileTemplate).filter_by(resource_type_id=resource_type_id)
        if min_level is not None:
            q = q.filter(ResourceTileTemplate.tile_level >= min_level)
        if max_level and max_level > 0:
            q = q.filter(ResourceTileTemplate.tile_level <= max_level)
        return q.order_by(ResourceTileTemplate.tile_level.desc()).all()
    finally:
        session.close()


def get_all_tile_templates():
    """Return all tile templates across all resource types."""
    session = get_session()
    try:
        return (
            session.query(ResourceTileTemplate)
            .order_by(ResourceTileTemplate.resource_type_id, ResourceTileTemplate.tile_level.desc())
            .all()
        )
    finally:
        session.close()


def add_tile_template(resource_type_id, tile_level, img_path, threshold=0.85, preview_image=None):
    """Add a new tile template. Returns the new template id."""
    session = get_session()
    try:
        template = ResourceTileTemplate(
            resource_type_id=resource_type_id,
            tile_level=int(tile_level),
            img_540p=img_path,
            img_threshold=float(threshold),
            preview_image=preview_image,
        )
        session.add(template)
        session.commit()
        return template.id
    finally:
        session.close()


def delete_tile_template(template_id):
    """Delete a tile template by id."""
    session = get_session()
    try:
        template = session.query(ResourceTileTemplate).get(template_id)
        if template:
            session.delete(template)
            session.commit()
    finally:
        session.close()
