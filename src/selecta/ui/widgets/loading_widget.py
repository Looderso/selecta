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


class LoadableWidget(QWidget):
    """Base class for widgets that can display a loading state."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the loadable widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._loading: bool = False
        self._loading_indicator: QLabel | None = None
        self._loading_message: QLabel | None = None
        self._content_widget: QWidget | None = None
        self._loading_widget: QWidget | None = None
        self._spinner_movie: QMovie | None = None

    def _create_loading_widget(self, message: str = "Loading...") -> QWidget:
        """Create a widget to display during loading state.

        Args:
            message: Loading message to display

        Returns:
            A widget that displays a loading indicator and message
        """
        loading_widget = QWidget(self)
        layout = QVBoxLayout(loading_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(10, 10, 10, 10)

        # Create spinner label
        spinner_label = QLabel()
        spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Create the spinner movie
        spinner_movie = QMovie("resources/spinner.gif")
        if spinner_movie.isValid():
            spinner_label.setMovie(spinner_movie)
            self._spinner_movie = spinner_movie
        else:
            # Fallback to a text indicator
            spinner_label.setText("⟳")
            spinner_label.setStyleSheet("font-size: 48px; color: #888; margin: 10px;")

        # Create message label
        message_label = QLabel(message)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setStyleSheet("color: #888; font-size: 14px; margin: 10px;")

        # Add to layout
        layout.addWidget(spinner_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Save references
        self._loading_indicator = spinner_label
        self._loading_message = message_label
        self._loading_widget = loading_widget

        return loading_widget

    def set_content_widget(self, widget: QWidget) -> None:
        """Set the main content widget.

        Args:
            widget: The widget to display as main content
        """
        self._content_widget = widget

    def show_loading(self, message: str = "Loading...") -> None:
        """Show loading state with the given message.

        Args:
            message: Message to display during loading
        """
        if not self._loading_widget:
            self._create_loading_widget(message)
        else:
            if self._loading_message:
                self._loading_message.setText(message)

        # Hide content widget
        if self._content_widget:
            self._content_widget.setVisible(False)

        # Show loading widget
        if self._loading_widget:
            self._loading_widget.setVisible(True)

        # Start animation
        if self._spinner_movie and self._spinner_movie.isValid():
            self._spinner_movie.start()

        self._loading = True

    def hide_loading(self) -> None:
        """Hide loading state and show content widget."""
        # Stop animation
        if self._spinner_movie and self._spinner_movie.isValid():
            self._spinner_movie.stop()

        # Hide loading widget
        if self._loading_widget:
            self._loading_widget.setVisible(False)

        # Show content widget
        if self._content_widget:
            self._content_widget.setVisible(True)

        self._loading = False

    def is_loading(self) -> bool:
        """Return whether the widget is in loading state.

        Returns:
            True if loading, False otherwise
        """
        return self._loading

    def update_loading_message(self, message: str) -> None:
        """Update the loading message.

        Args:
            message: New message to display
        """
        if self._loading_message:
            self._loading_message.setText(message)
