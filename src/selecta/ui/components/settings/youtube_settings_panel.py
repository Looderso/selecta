from PyQt6.QtWidgets import QGroupBox, QLabel, QScrollArea, QVBoxLayout, QWidget


class YouTubeSettingsPanel(QWidget):
    """Panel for YouTube-specific settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        # Main layout
        layout = QVBoxLayout(self)

        # Create scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # Header
        header = QLabel("YouTube Settings")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        content_layout.addWidget(header)

        # Search options group
        search_group = QGroupBox("Search Options")
        search_layout = QVBoxLayout(search_group)
        search_layout.addWidget(QLabel("YouTube search settings will appear here"))
        content_layout.addWidget(search_group)

        # Integration settings group
        integration_group = QGroupBox("Integration Settings")
        integration_layout = QVBoxLayout(integration_group)
        integration_layout.addWidget(QLabel("YouTube integration settings will appear here"))
        content_layout.addWidget(integration_group)

        # Add stretch to push groups to the top
        content_layout.addStretch(1)

        # Set up scroll area
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
