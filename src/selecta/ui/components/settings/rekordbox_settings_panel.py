from PyQt6.QtWidgets import QGroupBox, QLabel, QScrollArea, QVBoxLayout, QWidget


class RekordboxSettingsPanel(QWidget):
    """Panel for Rekordbox-specific settings."""

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
        header = QLabel("Rekordbox Settings")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        content_layout.addWidget(header)

        # Import settings group
        import_group = QGroupBox("Import Settings")
        import_layout = QVBoxLayout(import_group)
        import_layout.addWidget(QLabel("Rekordbox import settings will appear here"))
        content_layout.addWidget(import_group)

        # Export settings group
        export_group = QGroupBox("Export Settings")
        export_layout = QVBoxLayout(export_group)
        export_layout.addWidget(QLabel("Rekordbox export settings will appear here"))
        content_layout.addWidget(export_group)

        # Add stretch to push groups to the top
        content_layout.addStretch(1)

        # Set up scroll area
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
