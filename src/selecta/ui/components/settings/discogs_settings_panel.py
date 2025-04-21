from PyQt6.QtWidgets import QGroupBox, QLabel, QScrollArea, QVBoxLayout, QWidget


class DiscogsSettingsPanel(QWidget):
    """Panel for Discogs-specific settings."""

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
        header = QLabel("Discogs Settings")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        content_layout.addWidget(header)

        # Collection settings group
        collection_group = QGroupBox("Collection Settings")
        collection_layout = QVBoxLayout(collection_group)
        collection_layout.addWidget(QLabel("Discogs collection settings will appear here"))
        content_layout.addWidget(collection_group)

        # Metadata settings group
        metadata_group = QGroupBox("Metadata Settings")
        metadata_layout = QVBoxLayout(metadata_group)
        metadata_layout.addWidget(QLabel("Discogs metadata settings will appear here"))
        content_layout.addWidget(metadata_group)

        # Add stretch to push groups to the top
        content_layout.addStretch(1)

        # Set up scroll area
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
