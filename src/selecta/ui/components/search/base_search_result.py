"""Base class for search result items."""

from abc import abstractmethod
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget

from selecta.ui.components.search.utils.image_loader import get_image_loader


class BaseSearchResult(QWidget):
    """Abstract base class for search result items.

    This class provides the foundation for platform-specific search result items,
    standardizing signals, state management, and basic interaction behavior.
    """

    # Constants for layout
    THUMBNAIL_WIDTH = 54  # Width of the thumbnail image
    BUTTON_WIDTH = 60  # Width of the action buttons
    BUTTON_HEIGHT = 25  # Height of the action buttons
    LAYOUT_SPACING = 12  # Spacing between layout components

    # Common signals
    link_clicked = pyqtSignal(dict)  # Emitted when link button is clicked
    add_clicked = pyqtSignal(dict)  # Emitted when add button is clicked

    def __init__(self, item_data: dict[str, Any], parent=None):
        """Initialize the base search result.

        Args:
            item_data: Dictionary with item data from the platform API
            parent: Parent widget
        """
        super().__init__(parent)
        self.item_data = item_data

        # Common state properties
        self._can_add = False
        self._can_link = False
        self.is_hovered = False

        # Image handling properties
        self._image_loaded = False
        self._thumbnail_label: QLabel | None = None
        self._image_url = ""
        self._image_loader = get_image_loader()

        # Common widget setup
        self.setMouseTracking(True)  # Enable mouse tracking for hover events
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Call platform-specific UI setup
        self._setup_ui()

        # Load image after UI setup
        self._load_thumbnail()

    def _setup_ui(self) -> None:
        """Set up the UI components.

        This is now a concrete implementation that handles the common layout.
        Subclasses should override setup_content() to add their specific content.
        """
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(self.LAYOUT_SPACING)

        # Thumbnail image (fixed width on left)
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(self.THUMBNAIL_WIDTH, self.THUMBNAIL_WIDTH)
        self.thumbnail_label.setScaledContents(True)
        self.thumbnail_label.setStyleSheet("border-radius: 4px;")

        # Set up thumbnail loading
        self.set_thumbnail_label(self.thumbnail_label)
        main_layout.addWidget(self.thumbnail_label)

        # Create a stacked widget for the text content
        # This allows text to expand to full width when buttons are hidden
        # and contract when buttons are visible
        self.stack_widget = QStackedWidget()

        # Text content widget when buttons are hidden (full width)
        self.full_width_container = QWidget()
        full_width_layout = QVBoxLayout(self.full_width_container)
        full_width_layout.setContentsMargins(0, 0, 0, 0)
        full_width_layout.setSpacing(1)
        self.full_width_text_layout = full_width_layout

        # Text content widget when buttons are visible (reduced width)
        self.reduced_width_container = QWidget()
        reduced_width_layout = QVBoxLayout(self.reduced_width_container)
        reduced_width_layout.setContentsMargins(0, 0, 0, 0)
        reduced_width_layout.setSpacing(1)
        self.reduced_width_text_layout = reduced_width_layout

        # Use full width by default (no hover)
        self.text_layout = self.full_width_text_layout

        # Add both containers to the stack widget
        self.stack_widget.addWidget(self.full_width_container)
        self.stack_widget.addWidget(self.reduced_width_container)

        # By default, show the full width container
        self.stack_widget.setCurrentWidget(self.full_width_container)

        # Add stack widget to main layout
        main_layout.addWidget(self.stack_widget, 1)  # 1 = stretch factor

        # Buttons container (fixed width on right)
        self.buttons_container = QWidget()
        self.buttons_container.setFixedWidth(self.BUTTON_WIDTH)
        self.buttons_layout = QVBoxLayout(self.buttons_container)
        self.buttons_layout.setSpacing(6)
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)

        # Link button
        self.link_button = QPushButton("Link")
        self.link_button.setFixedSize(self.BUTTON_WIDTH, self.BUTTON_HEIGHT)
        self.link_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.link_button.clicked.connect(self._on_link_clicked)
        self.link_button.setEnabled(False)
        self.buttons_layout.addWidget(self.link_button)

        # Add button
        self.add_button = QPushButton("Add")
        self.add_button.setFixedSize(self.BUTTON_WIDTH, self.BUTTON_HEIGHT)
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_button.clicked.connect(self._on_add_clicked)
        self.add_button.setEnabled(False)
        self.buttons_layout.addWidget(self.add_button)

        # Add buttons container to main layout with a fixed width
        main_layout.addWidget(self.buttons_container)

        # Hide buttons initially
        self.buttons_container.setVisible(False)

        # Set minimal width for the content
        self.setMinimumWidth(self.THUMBNAIL_WIDTH + self.BUTTON_WIDTH + 100)

        # Set up platform-specific content
        self.setup_content()

    @abstractmethod
    def setup_content(self) -> None:
        """Set up the platform-specific content.

        This method should be implemented by subclasses to create
        platform-specific UI elements and add them to self.text_layout.
        """
        pass

    def update_button_state(self, can_add: bool = False, can_link: bool = False) -> None:
        """Update the state of the buttons based on current selection.

        Args:
            can_add: Whether tracks can be added to a playlist
            can_link: Whether tracks can be linked with a selected track
        """
        self._can_add = can_add
        self._can_link = can_link
        self._update_button_visibility()

    def _update_button_visibility(self) -> None:
        """Update the visibility and state of action buttons."""
        if self.is_hovered:
            # When hovering:
            # 1. Show the buttons container
            self.buttons_container.setVisible(True)

            # 2. Set enabled state for buttons
            self.link_button.setEnabled(self._can_link)
            self.add_button.setEnabled(self._can_add)

            # 3. Switch to reduced width text layout
            self.stack_widget.setCurrentWidget(self.reduced_width_container)
            self.text_layout = self.reduced_width_text_layout
        else:
            # When not hovering:
            # 1. Hide the buttons container
            self.buttons_container.setVisible(False)

            # 2. Switch to full width text layout
            self.stack_widget.setCurrentWidget(self.full_width_container)
            self.text_layout = self.full_width_text_layout

        # Update the text elision for both layouts
        self._update_elided_text()

    # Common event handlers
    def enterEvent(self, event) -> None:
        """Handle mouse enter events to show buttons.

        Args:
            event: The enter event
        """
        self.is_hovered = True
        self._update_button_visibility()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """Handle mouse leave events to hide buttons.

        Args:
            event: The leave event
        """
        self.is_hovered = False
        self._update_button_visibility()
        super().leaveEvent(event)

    def _on_link_clicked(self) -> None:
        """Handle link button click."""
        self.link_clicked.emit(self.item_data)

    def _on_add_clicked(self) -> None:
        """Handle add button click."""
        self.add_clicked.emit(self.item_data)

    @abstractmethod
    def get_title(self) -> str:
        """Get the title of the search result item.

        Returns:
            Title string
        """
        pass

    @abstractmethod
    def get_artist(self) -> str:
        """Get the artist/author/creator of the search result item.

        Returns:
            Artist string (may be empty if not applicable)
        """
        pass

    @abstractmethod
    def get_image_url(self) -> str:
        """Get the image/thumbnail URL for the search result item.

        Returns:
            URL string (may be empty if not available)
        """
        pass

    def set_thumbnail_label(self, label: QLabel) -> None:
        """Set the label that will display the thumbnail.

        Args:
            label: QLabel widget to display the thumbnail
        """
        self._thumbnail_label = label

        # Create placeholder
        placeholder = QPixmap(self._thumbnail_label.width(), self._thumbnail_label.height())
        placeholder.fill(Qt.GlobalColor.darkGray)
        self._thumbnail_label.setPixmap(placeholder)

        # Connect to image loader signals
        self._image_loader.image_loaded.connect(self._on_image_loaded)

    def _load_thumbnail(self) -> None:
        """Load the thumbnail image."""
        # Get image URL
        self._image_url = self.get_image_url()

        # If no URL or no label, just return
        if not self._image_url or not self._thumbnail_label:
            return

        # Check if already in cache
        cached_pixmap = self._image_loader.get_cached_image(self._image_url)
        if cached_pixmap:
            self._set_thumbnail(cached_pixmap)
            return

        # Load the image
        self._image_loader.load_image(self._image_url)

    def _on_image_loaded(self, url: str, pixmap: QPixmap) -> None:
        """Handle loaded image from URL.

        Args:
            url: The URL of the loaded image
            pixmap: The loaded image pixmap
        """
        # Check if this is the image we requested
        if url == self._image_url and self._thumbnail_label:
            self._set_thumbnail(pixmap)

    def _set_thumbnail(self, pixmap: QPixmap) -> None:
        """Set the thumbnail image.

        Args:
            pixmap: The image pixmap to set
        """
        if not self._thumbnail_label:
            return

        # Scale the pixmap to the label size
        scaled_pixmap = pixmap.scaled(
            self._thumbnail_label.width(),
            self._thumbnail_label.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # Set the pixmap
        self._thumbnail_label.setPixmap(scaled_pixmap)
        self._image_loaded = True

    # This method is no longer needed as the text layout is created directly in _setup_ui
    # Kept for reference in case subclasses call it
    def setup_text_content(self, layout: QHBoxLayout) -> QVBoxLayout:
        """This method is kept for backwards compatibility.

        The text layout is now created directly in _setup_ui.

        Args:
            layout: The main horizontal layout (ignored)

        Returns:
            The text layout that was already created
        """
        return self.text_layout

    def create_elided_label(self, text: str, object_name: str) -> QLabel:
        """Create a QLabel with elided text that shows the full text on hover.

        This creates two identical labels - one for each layout, and returns the
        reference to the "current" one. The reference will switch based on hover state.

        Args:
            text: The text to display
            object_name: The object name to set on the label

        Returns:
            QLabel with elided text and tooltip (current one)
        """
        # Create and setup the label for full width layout
        full_width_label = QLabel(text)
        full_width_label.setObjectName(object_name)
        full_width_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        full_width_label.setToolTip(text)
        full_width_label.setProperty("fullText", text)
        full_width_label.setProperty("needsElision", True)
        self.full_width_text_layout.addWidget(full_width_label)

        # Create and setup an identical label for reduced width layout
        reduced_width_label = QLabel(text)
        reduced_width_label.setObjectName(object_name)
        reduced_width_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        reduced_width_label.setToolTip(text)
        reduced_width_label.setProperty("fullText", text)
        reduced_width_label.setProperty("needsElision", True)
        self.reduced_width_text_layout.addWidget(reduced_width_label)

        # Store reference to paired labels
        full_width_label.setProperty("paired_label", reduced_width_label)
        reduced_width_label.setProperty("paired_label", full_width_label)

        # Return the current label based on hover state
        return full_width_label

    def resizeEvent(self, event):
        """Handle resize events to update elided text.

        Args:
            event: The resize event
        """
        super().resizeEvent(event)
        self._update_elided_text()

    def _update_elided_text(self):
        """Update the elided text based on available width.

        This is called both on resize events and when buttons visibility changes.
        Handles elision for both full width and reduced width layouts.
        """
        # Calculate total content width (minus thumbnail and spacing)
        total_width = self.width() - self.THUMBNAIL_WIDTH - (self.LAYOUT_SPACING * 2)

        # Calculate the two different available widths
        full_width = total_width  # No buttons visible
        reduced_width = total_width - self.BUTTON_WIDTH - self.LAYOUT_SPACING  # Buttons visible

        if full_width <= 0 or reduced_width <= 0:
            return

        # Update labels in full width layout
        for label in self.full_width_container.findChildren(QLabel):
            if label.property("needsElision") and label.property("fullText"):
                full_text = label.property("fullText")
                font_metrics = label.fontMetrics()
                elided_text = font_metrics.elidedText(full_text, Qt.TextElideMode.ElideRight, full_width)
                label.setText(elided_text)

        # Update labels in reduced width layout
        for label in self.reduced_width_container.findChildren(QLabel):
            if label.property("needsElision") and label.property("fullText"):
                full_text = label.property("fullText")
                font_metrics = label.fontMetrics()
                elided_text = font_metrics.elidedText(full_text, Qt.TextElideMode.ElideRight, reduced_width)
                label.setText(elided_text)
