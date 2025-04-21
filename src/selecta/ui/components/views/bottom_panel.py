"""Bottom content placeholder for the main window."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class BottomContent(QWidget):
    """Placeholder component for the bottom section of the main window."""

    def __init__(self, parent=None) -> None:
        """Initialize the bottom content area."""
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Create a title
        title = QLabel("Bottom Section")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # Description label
        description = QLabel("This section will contain additional functionality in the future.")
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        description.setStyleSheet("color: #888;")
        layout.addWidget(description)
