from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QWidget


class SettingsNavigation(QWidget):
    """Navigation sidebar for settings categories."""

    category_changed = pyqtSignal(str)  # Emits the selected category name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsNavigation")
        self.setFixedWidth(200)
        self.setStyleSheet("""
            #settingsNavigation {
                background-color: #252525;
                border-right: 1px solid #333;
            }
            QPushButton {
                text-align: left;
                padding: 12px 15px;
                border: none;
                border-radius: 0;
                background-color: transparent;
                color: #CCCCCC;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton.active {
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                font-weight: bold;
                border-left: 3px solid #3498db;
            }
        """)
        self._setup_ui()
        self._current_category = "general"

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(0)

        # Create category buttons
        self.general_button = self._create_category_button("General", "general")
        self.auth_button = self._create_category_button("Authentication", "auth")
        self.rekordbox_button = self._create_category_button("Rekordbox", "rekordbox")
        self.discogs_button = self._create_category_button("Discogs", "discogs")
        self.spotify_button = self._create_category_button("Spotify", "spotify")
        self.youtube_button = self._create_category_button("YouTube", "youtube")

        # Add buttons to layout
        layout.addWidget(self.general_button)
        layout.addWidget(self.auth_button)
        layout.addWidget(self.rekordbox_button)
        layout.addWidget(self.discogs_button)
        layout.addWidget(self.spotify_button)
        layout.addWidget(self.youtube_button)

        # Add stretch to push buttons to the top
        layout.addStretch(1)

        # Set initial state
        self.set_active_category("general")

    def _create_category_button(self, label, category):
        """Create a category button.

        Args:
            label: Button text
            category: Category identifier

        Returns:
            QPushButton for the category
        """
        button = QPushButton(label)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(lambda: self._on_category_selected(category))
        return button

    def _on_category_selected(self, category):
        """Handle category selection.

        Args:
            category: Selected category identifier
        """
        # Update button states
        self.set_active_category(category)

        # Emit signal
        self.category_changed.emit(category)

    def set_active_category(self, category):
        """Set the active category and update UI.

        Args:
            category: Category to activate
        """
        # Reset all buttons
        for button in [
            self.general_button,
            self.auth_button,
            self.rekordbox_button,
            self.discogs_button,
            self.spotify_button,
            self.youtube_button,
        ]:
            button.setProperty("class", "")
            button.setStyleSheet("")

        # Set active button
        if category == "general":
            self.general_button.setProperty("class", "active")
            self.general_button.setStyleSheet(
                "background-color: rgba(255, 255, 255, 0.2); \
                color: white; font-weight: bold; border-left: 3px solid #3498db;"
            )
        elif category == "auth":
            self.auth_button.setProperty("class", "active")
            self.auth_button.setStyleSheet(
                "background-color: rgba(255, 255, 255, 0.2); \
                color: white; font-weight: bold; border-left: 3px solid #3498db;"
            )
        elif category == "rekordbox":
            self.rekordbox_button.setProperty("class", "active")
            self.rekordbox_button.setStyleSheet(
                "background-color: rgba(255, 255, 255, 0.2); \
                color: white; font-weight: bold; border-left: 3px solid #3498db;"
            )
        elif category == "discogs":
            self.discogs_button.setProperty("class", "active")
            self.discogs_button.setStyleSheet(
                "background-color: rgba(255, 255, 255, 0.2); \
                color: white; font-weight: bold; border-left: 3px solid #3498db;"
            )
        elif category == "spotify":
            self.spotify_button.setProperty("class", "active")
            self.spotify_button.setStyleSheet(
                "background-color: rgba(255, 255, 255, 0.2); \
                color: white; font-weight: bold; border-left: 3px solid #3498db;"
            )
        elif category == "youtube":
            self.youtube_button.setProperty("class", "active")
            self.youtube_button.setStyleSheet(
                "background-color: rgba(255, 255, 255, 0.2); \
                color: white; font-weight: bold; border-left: 3px solid #3498db;"
            )

        self._current_category = category
