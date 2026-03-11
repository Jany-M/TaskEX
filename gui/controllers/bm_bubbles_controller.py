"""
Bot Manager Bubbles Controller - Initialize and manage the app-wide Bubble Manager UI.
Displays and allows configuration of bubble template images, thresholds, etc.
"""

from core.custom_widgets.FlowLayout import FlowLayout
from core.services.bubble_service import get_all_bubble_types
from gui.widgets.BubbleProfileWidget import BubbleProfileWidget


def init_bm_bubbles_ui(main_window):
    """Initialize the Bubble Manager UI in the Bot Manager with all bubble types."""

    # Get the container frame
    bubbles_list_frame = main_window.widgets.bubbles_list_frame

    # Set up the Flow Layout for bubbles
    flow_layout = FlowLayout(bubbles_list_frame)
    flow_layout.setObjectName("bubbles_list_flow_layout")
    setattr(main_window.widgets, flow_layout.objectName(), flow_layout)

    # Set the flow layout to the container frame
    bubbles_list_frame.setLayout(flow_layout)

    # Get all the bubble types
    bubble_types = get_all_bubble_types()

    # Add a profile widget for each bubble type
    for bubble in bubble_types:
        add_bubble_to_frame(main_window, bubble)


def add_bubble_to_frame(main_window, bubble):
    """Add a BubbleProfileWidget to the flow layout."""
    flow_layout = main_window.widgets.bubbles_list_flow_layout

    widget = BubbleProfileWidget(data=bubble)
    setattr(main_window.widgets, widget.objectName(), widget)

    # Set a reasonable fixed size for the widget
    widget.setFixedWidth(450)
    flow_layout.addWidget(widget)
