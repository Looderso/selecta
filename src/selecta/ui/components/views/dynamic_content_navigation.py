from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class DynamicContentNavigationBar(QWidget):
    """Navigation bar for switching between dynamic content views."""

    view_changed = pyqtSignal(str)  # Emits the selected view name

    def __init__(self, parent=None):
        """Initialize the navigation bar.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()
        self._current_view = "details"

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Create view buttons
        self.details_button = QPushButton("Details")
        self.details_button.setCheckable(True)
        self.details_button.clicked.connect(lambda: self._on_view_selected("details"))

        self.search_button = QPushButton("Search")
        self.search_button.setCheckable(True)
        self.search_button.clicked.connect(lambda: self._on_view_selected("search"))

        # Add buttons to layout
        layout.addWidget(self.details_button)
        layout.addWidget(self.search_button)
        layout.addStretch(1)

        # Set initial state
        self.details_button.setChecked(True)

    def _on_view_selected(self, view_name):
        """Handle view selection.

        Args:
            view_name: Name of the selected view
        """
        # Update button states
        self.details_button.setChecked(view_name == "details")
        self.search_button.setChecked(view_name == "search")

        # Update current view
        self._current_view = view_name

        # Emit signal
        self.view_changed.emit(view_name)

    def set_current_view(self, view_name):
        """Programmatically set the current view.

        Args:
            view_name: View name to set
        """
        if view_name != self._current_view:
            self._on_view_selected(view_name)

    def set_details_enabled(self, enabled):
        """Enable or disable the details button based on selection state.

        Args:
            enabled: Whether the details button should be enabled
        """
        self.details_button.setEnabled(enabled)
