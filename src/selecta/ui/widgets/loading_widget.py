"""Loading widget for displaying loading states."""

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMovie
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class LoadingWidget(QWidget):
    """A widget that displays a loading spinner and message."""

    def __init__(self, message: str = "Loading...", parent: QWidget | None = None) -> None:
        """Initialize the loading widget.

        Args:
            message: The message to display
            parent: Parent widget
        """
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(10, 10, 10, 10)

        # Create spinner label
        self.spinner_label = QLabel()
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create the spinner movie
        self.spinner_movie = QMovie("resources/spinner.gif")
        if self.spinner_movie.isValid():
            self.spinner_label.setMovie(self.spinner_movie)
            self.spinner_movie.start()
        else:
            # Fallback to a text indicator
            self.spinner_label.setText("⟳")
            self.spinner_label.setStyleSheet("font-size: 48px; color: #888; margin: 10px;")

        # Create message label
        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setStyleSheet("color: #888; font-size: 14px; margin: 10px;")

        # Add to layout
        layout.addWidget(self.spinner_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message_label, alignment=Qt.AlignmentFlag.AlignCenter)

    def set_message(self, message: str) -> None:
        """Update the loading message.

        Args:
            message: The new message to display
        """
        self.message_label.setText(message)
        
    def showEvent(self, event: Any) -> None:
        """Handle show event to start animation.

        Args:
            event: The show event
        """
        super().showEvent(event)
        if self.spinner_movie.isValid():
            self.spinner_movie.start()

    def hideEvent(self, event: Any) -> None:
        """Handle hide event to stop animation.

        Args:
            event: The hide event
        """
        if self.spinner_movie.isValid():
            self.spinner_movie.stop()
        super().hideEvent(event)