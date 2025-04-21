from PyQt6.QtWidgets import QGroupBox, QLabel, QScrollArea, QVBoxLayout, QWidget

from selecta.ui.widgets.folder_selection_widget import FolderSelectionWidget


class GeneralSettingsPanel(QWidget):
    """Panel for general application settings."""

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
        header = QLabel("General Settings")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        content_layout.addWidget(header)

        # Folder selection group
        folder_group = QGroupBox("Local Database")
        folder_layout = QVBoxLayout(folder_group)

        # Migrate folder selection widget from side drawer
        self.folder_selection = FolderSelectionWidget()
        folder_layout.addWidget(self.folder_selection)

        content_layout.addWidget(folder_group)

        # Application settings group
        app_group = QGroupBox("Application Settings")
        app_layout = QVBoxLayout(app_group)

        # Add application settings here (theme, language, etc.)
        # Placeholder for now
        app_layout.addWidget(QLabel("Application settings will appear here"))

        content_layout.addWidget(app_group)

        # Add stretch to push groups to the top
        content_layout.addStretch(1)

        # Set up scroll area
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
