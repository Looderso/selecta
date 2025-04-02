# src/selecta/ui/utils/loading.py

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QMovie
from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout


class LoadingOverlay(QDialog):
    """Creates a modal loading overlay with an animated spinner and message."""

    def __init__(self, parent=None, message="Loading...", modal=True):
        super().__init__(parent)

        # Set up the dialog to appear like an overlay
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        if modal:
            self.setModal(True)

        # Create semi-transparent background
        self.setStyleSheet("background-color: rgba(0, 0, 0, 150);")

        # Main layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create label for the spinner animation
        self.spinner_label = QLabel()
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create the spinner movie
        self.spinner_movie = QMovie("resources/spinner.gif")
        if self.spinner_movie.isValid():
            self.spinner_label.setMovie(self.spinner_movie)
        else:
            # Fallback to a text indicator
            self.spinner_label.setText("⟳")
            self.spinner_label.setStyleSheet("font-size: 48px; color: white;")

        layout.addWidget(self.spinner_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Message label
        self.message_label = QLabel(message)
        self.message_label.setStyleSheet(
            "color: white; font-size: 16px; background-color: transparent; margin-top: 10px;"
        )
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message_label)

    def showEvent(self, event):
        """Handle the show event."""
        super().showEvent(event)

        # Start the animation
        if self.spinner_movie.isValid():
            self.spinner_movie.start()

        # Schedule positioning after the widget is shown
        # This is important because we need the parent to be fully laid out
        QTimer.singleShot(0, self.position_over_parent)

    def position_over_parent(self):
        """Position the overlay correctly over its parent widget."""
        if not self.parent():
            return

        # Get the parent's global position
        parent_pos = self.parent().mapToGlobal(self.parent().rect().topLeft())
        parent_size = self.parent().size()

        # Map parent's global position to position relative to the overlay's parent
        # (which might be different from the widget we want to cover)
        overlay_parent = self.parentWidget()
        if overlay_parent:
            parent_pos = overlay_parent.mapFromGlobal(parent_pos)

        # Set the overlay geometry to exactly match the parent's rectangle
        self.setGeometry(parent_pos.x(), parent_pos.y(), parent_size.width(), parent_size.height())

    def hideEvent(self, event):
        """Handle the hide event."""
        if self.spinner_movie.isValid():
            self.spinner_movie.stop()
        super().hideEvent(event)

    def set_message(self, message):
        """Update the loading message."""
        self.message_label.setText(message)


class LoadingManager:
    """Manages loading overlays for different widgets."""

    _overlays = {}

    @classmethod
    def show_loading(cls, parent, message="Loading...", widget_key=None):
        """Show a loading overlay on the specified parent widget.

        Args:
            parent: The parent widget
            message: Loading message to display
            widget_key: Optional key to identify this overlay later
        """
        if not parent:
            return

        key = widget_key or id(parent)

        # Find the correct parent for the overlay
        # This should be the main window or frame that contains the widget
        top_level_parent = parent.window()

        # Create a new overlay if one doesn't exist
        if key not in cls._overlays:
            cls._overlays[key] = LoadingOverlay(top_level_parent, message)
            # Store the original parent widget that we want to cover
            cls._overlays[key].target_widget = parent

        # Update the message and show
        overlay = cls._overlays[key]
        overlay.set_message(message)

        # Make sure the overlay's target is correctly set
        overlay.target_widget = parent

        # Show the overlay - positioning will happen in showEvent
        overlay.show()

        # Force an immediate position update
        overlay.position_over_parent()

    @classmethod
    def hide_loading(cls, parent=None, widget_key=None):
        """Hide the loading overlay.

        Args:
            parent: The parent widget
            widget_key: Optional key to identify the overlay
        """
        key = widget_key or (id(parent) if parent else None)

        if key and key in cls._overlays:
            cls._overlays[key].hide()
