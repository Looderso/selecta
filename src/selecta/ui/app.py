# src/selecta/ui/app.py
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

from selecta.ui.components.platform_auth_panel import PlatformAuthPanel


class SelectaMainWindow(QMainWindow):
    """Main application window for Selecta."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        self.setWindowTitle("Selecta")
        self.setMinimumSize(800, 600)

        # Setup UI components
        self._setup_ui()

    def _setup_ui(self):
        """Set up the main UI components."""
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Add title
        title_label = QLabel("Platform Authentication")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        main_layout.addWidget(title_label)

        # Add subtitle
        subtitle_label = QLabel("Connect your accounts to synchronize your music across platforms")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("font-size: 14px; color: #888; margin-bottom: 20px;")
        main_layout.addWidget(subtitle_label)

        # Add authentication panel
        self.auth_panel = PlatformAuthPanel()
        main_layout.addWidget(self.auth_panel)

        # Add spacer to push everything to the top
        main_layout.addStretch(1)


def run_app():
    """Run the PyQt application."""
    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("Selecta")
    app.setOrganizationName("Looderso")

    # Apply basic styling
    app.setStyle("Fusion")

    # Apply dark theme with custom styling
    app.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: #2D2D30;
            color: #FFFFFF;
        }
        QPushButton {
            background-color: #0078D7;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #1988E0;
        }
        QPushButton:pressed {
            background-color: #006CC1;
        }
    """)

    # Create and show the main window
    window = SelectaMainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(run_app())
