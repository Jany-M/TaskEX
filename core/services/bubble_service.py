from db.db_setup import get_session
from db.models import BubbleType


BUBBLE_DISPLAY_NAMES = {
    1: "8 Hour Truce Agreement",
    2: "24 Hour Truce Agreement",
    3: "3 Day Truce Agreement",
    4: "7 Day Truce Agreement",
}


def get_bubble_display_name(bubble_or_id):
    bubble_id = bubble_or_id.id if hasattr(bubble_or_id, 'id') else bubble_or_id
    return BUBBLE_DISPLAY_NAMES.get(bubble_id, getattr(bubble_or_id, 'name', str(bubble_or_id)))


def get_all_bubble_types():
    """Return all four seeded bubble types ordered by id."""
    session = get_session()
    try:
        return session.query(BubbleType).order_by(BubbleType.id).all()
    finally:
        session.close()


def update_bubble_type_template(bubble_id, img_path, threshold=0.85):
    """Update the template image path and matching threshold for a bubble type."""
    session = get_session()
    try:
        bubble = session.query(BubbleType).get(bubble_id)
        if bubble:
            bubble.img_540p = img_path
            bubble.img_threshold = float(threshold)
            session.commit()
    finally:
        session.close()


def clear_bubble_type_template(bubble_id):
    """Remove the template from a bubble type."""
    session = get_session()
    try:
        bubble = session.query(BubbleType).get(bubble_id)
        if bubble:
            bubble.img_540p = None
            bubble.preview_image = None
            session.commit()
    finally:
        session.close()
