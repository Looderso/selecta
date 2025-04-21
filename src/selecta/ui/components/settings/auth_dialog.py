from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton, QVBoxLayout

from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.platform_factory import PlatformFactory


class AuthenticationDialog(QDialog):
    """Unified authentication dialog for all platforms."""

    def __init__(self, platform_name, parent=None):
        """Initialize the authentication dialog.

        Args:
            platform_name: Name of the platform to authenticate
            parent: Parent widget
        """
        super().__init__(parent)
        self.platform_name = platform_name
        self.settings_repo = SettingsRepository()
        self.platform_client = PlatformFactory.create(platform_name, self.settings_repo)

        self.auth_success = False

        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(f"Connect to {self.platform_name}")
        self.setFixedSize(QSize(400, 250))
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel(f"Connect to {self.platform_name}")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        # Description
        description = QLabel(
            f"You'll be redirected to authorize {self.platform_name} access. "
            "After authorization, you'll be returned to Selecta automatically."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # Progress indicator
        self.progress_label = QLabel("Ready to connect...")
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Button area
        button_layout = QHBoxLayout()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.connect_button = QPushButton("Connect Now")
        self.connect_button.setDefault(True)
        self.connect_button.clicked.connect(self._start_authentication)
        button_layout.addWidget(self.connect_button)

        layout.addStretch(1)
        layout.addLayout(button_layout)

    def _start_authentication(self):
        """Start the authentication process."""
        self.progress_label.setText("Authenticating...")
        self.progress_bar.setVisible(True)
        self.connect_button.setEnabled(False)

        # Start authentication
        try:
            # Use platform client to authenticate
            success = self.platform_client.authenticate()

            if success:
                self.progress_label.setText("Authentication successful!")
                self.auth_success = True

                # Allow time to see success message
                from PyQt6.QtCore import QTimer

                QTimer.singleShot(1000, self.accept)
            else:
                self.progress_label.setText("Authentication failed.")
                self.progress_bar.setVisible(False)
                self.connect_button.setEnabled(True)

                QMessageBox.critical(
                    self,
                    "Authentication Failed",
                    f"Failed to authenticate with {self.platform_name}. Please try again.",
                    QMessageBox.StandardButton.Ok,
                    QMessageBox.StandardButton.Ok,
                )
        except Exception as e:
            self.progress_label.setText("Error during authentication.")
            self.progress_bar.setVisible(False)
            self.connect_button.setEnabled(True)

            QMessageBox.critical(
                self,
                "Authentication Error",
                f"An error occurred during authentication: {str(e)}",
                QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.Ok,
            )

    @staticmethod
    def authenticate_platform(platform_name, parent=None):
        """Static method to authenticate a platform.

        Args:
            platform_name: Name of the platform to authenticate
            parent: Parent widget

        Returns:
            bool: True if authentication was successful, False otherwise
        """
        dialog = AuthenticationDialog(platform_name, parent)
        result = dialog.exec()

        return result == QDialog.DialogCode.Accepted and dialog.auth_success
