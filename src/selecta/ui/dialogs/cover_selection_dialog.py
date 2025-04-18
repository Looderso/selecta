"""Dialog for selecting cover images from platforms."""

from typing import Any
from urllib.request import Request, urlopen

from loguru import logger
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from selecta.core.data.models.db import Track
from selecta.core.utils.path_helper import get_resource_path


class ImageDownloader(QThread):
    """Thread for downloading images in background."""

    # Signal emitted when an image has been downloaded
    image_downloaded = pyqtSignal(str, QPixmap, dict)  # platform, pixmap, metadata

    # Signal for download progress
    download_progress = pyqtSignal(int, int)  # current, total

    def __init__(self, platform_images: dict[str, list]):
        """Initialize the image downloader.

        Args:
            platform_images: Dictionary mapping platform names to lists of image data
        """
        super().__init__()
        self.platform_images = platform_images
        self.abort = False

    def run(self):
        """Run the image downloading thread."""
        total_images = sum(len(images) for images in self.platform_images.values())
        current = 0

        for platform_name, images_data in self.platform_images.items():
            for image_data in images_data:
                if self.abort:
                    return

                if "url" not in image_data:
                    continue

                try:
                    # Download the image
                    url = image_data["url"]
                    pixmap = self._download_image(url)

                    if not pixmap.isNull():
                        # Emit the downloaded image
                        self.image_downloaded.emit(platform_name, pixmap, image_data)
                except Exception as e:
                    logger.error(f"Error downloading image from {platform_name}: {e}")

                # Update progress
                current += 1
                self.download_progress.emit(current, total_images)

    def _download_image(self, url: str) -> QPixmap:
        """Download an image from a URL.

        Args:
            url: URL to download from

        Returns:
            QPixmap containing the downloaded image
        """
        try:
            # Create request with headers to mimic a browser
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            req = Request(url, headers=headers)

            # Download the image
            with urlopen(req, timeout=10) as response:
                image_data = response.read()

            # Create pixmap from image data
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)

            return pixmap
        except Exception as e:
            logger.error(f"Error downloading image from {url}: {e}")
            return QPixmap()


class CoverImageItem(QWidget):
    """Widget that displays a cover image option from a platform."""

    # Signal emitted when an image is selected
    selected = pyqtSignal(QPixmap, dict)  # Pixmap and image metadata

    def __init__(self, pixmap: QPixmap, platform_name: str, metadata: dict, parent=None):
        """Initialize the cover image item.

        Args:
            pixmap: The image pixmap
            platform_name: Name of the platform (e.g., "spotify")
            metadata: Image metadata (url, dimensions, etc.)
            parent: Parent widget
        """
        super().__init__(parent)
        self.pixmap = pixmap
        self.platform_name = platform_name
        self.metadata = metadata
        self.is_selected = False

        self.setFixedSize(220, 250)  # Fixed size for consistent layout
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Main layout
        layout = QVBoxLayout(self)

        # Image label with border
        self.image_label = QLabel()
        self.image_label.setFixedSize(200, 200)
        self.image_label.setScaledContents(True)
        self.image_label.setPixmap(self.pixmap)
        self.image_label.setStyleSheet("border: 2px solid #555; border-radius: 4px;")

        # Platform label
        self.platform_label = QLabel(f"{platform_name.capitalize()}")
        self.platform_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Info label (resolution, etc.)
        width = metadata.get("width", "?")
        height = metadata.get("height", "?")
        self.info_label = QLabel(f"{width}x{height}")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Add to layout
        layout.addWidget(self.image_label, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.platform_label, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label, 0, Qt.AlignmentFlag.AlignCenter)

    def mousePressEvent(self, event):
        """Handle mouse click events.

        Args:
            event: Mouse event
        """
        self.selected.emit(self.pixmap, self.metadata)
        self.setSelected(True)
        super().mousePressEvent(event)

    def setSelected(self, selected: bool):
        """Set whether this image is selected.

        Args:
            selected: Whether the image is selected
        """
        self.is_selected = selected
        if selected:
            self.image_label.setStyleSheet("border: 3px solid #1DB954; border-radius: 4px;")
        else:
            self.image_label.setStyleSheet("border: 2px solid #555; border-radius: 4px;")


class CoverSelectionDialog(QDialog):
    """Dialog for selecting cover images from platforms."""

    def __init__(self, track: Track, platform_images: dict[str, Any], parent=None):
        """Initialize the cover selection dialog.

        Args:
            track: Track object to update with the selected cover
            platform_images: Dictionary of platform image data by platform name
            parent: Parent widget
        """
        super().__init__(parent)
        self.track = track
        self.platform_images = platform_images
        self.selected_image = None
        self.selected_metadata = None
        self.image_items = {}  # Map of URL to image item widget

        self.setWindowTitle("Select Cover Image")
        self.setMinimumSize(600, 400)

        # Main layout
        main_layout = QVBoxLayout(self)

        # Top label
        top_label = QLabel("Select a cover image from available platforms:")
        main_layout.addWidget(top_label)

        # Progress bar for image downloads
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # Create scroll area for images
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Container widget for images
        scroll_content = QWidget()
        self.images_layout = QHBoxLayout(scroll_content)
        self.images_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.images_layout.setContentsMargins(10, 10, 10, 10)
        self.images_layout.setSpacing(15)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # Selected image preview
        preview_layout = QHBoxLayout()
        preview_label = QLabel("Selected:")
        self.preview_image = QLabel()
        self.preview_image.setFixedSize(150, 150)
        self.preview_image.setScaledContents(True)
        self.preview_image.setStyleSheet("border: 1px solid #555;")

        # Set placeholder image
        placeholder = QPixmap(150, 150)
        placeholder.fill(Qt.GlobalColor.darkGray)
        self.preview_image.setPixmap(placeholder)

        preview_layout.addWidget(preview_label)
        preview_layout.addWidget(self.preview_image)
        preview_layout.addStretch(1)

        main_layout.addLayout(preview_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        # Disable OK button until an image is selected
        self.ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setEnabled(False)

        main_layout.addWidget(button_box)

        # Add placeholder image items
        self._add_platform_images()

        # Start downloading actual images
        self._start_image_download()

    def closeEvent(self, event):
        """Handle dialog close event to abort downloads.

        Args:
            event: Close event
        """
        if hasattr(self, "downloader") and self.downloader.isRunning():
            self.downloader.abort = True
            self.downloader.wait()
        super().closeEvent(event)

    def _add_platform_images(self):
        """Add platform images to the dialog with placeholders."""
        try:
            # Add placeholder images from each platform
            all_items = []

            for platform_name, images_data in self.platform_images.items():
                if not images_data:
                    continue

                for image_data in images_data:
                    # Skip if no URL
                    if "url" not in image_data:
                        continue

                    # Create a placeholder
                    try:
                        # Use platform icon as placeholder until real image is downloaded
                        pixmap = self._get_platform_pixmap(platform_name, 200, 200)

                        # Create image item
                        image_item = CoverImageItem(
                            pixmap=pixmap, platform_name=platform_name, metadata=image_data
                        )
                        image_item.selected.connect(self._on_image_selected)

                        # Store item reference by URL
                        self.image_items[image_data["url"]] = image_item

                        # Add to layout
                        self.images_layout.addWidget(image_item)
                        all_items.append(image_item)
                    except Exception as e:
                        logger.error(f"Error creating placeholder for {platform_name}: {e}")

            # If no images were added, show a message
            if not all_items:
                no_images_label = QLabel("No cover images available from connected platforms")
                no_images_label.setStyleSheet("color: #888; font-size: 14px;")
                self.images_layout.addWidget(no_images_label)

        except Exception as e:
            logger.error(f"Error adding platform images: {e}")

    def _start_image_download(self):
        """Start downloading actual images from URLs."""
        # Create and configure the image downloader
        self.downloader = ImageDownloader(self.platform_images)
        self.downloader.image_downloaded.connect(self._on_image_downloaded)
        self.downloader.download_progress.connect(self._on_download_progress)

        # Start the download thread
        self.downloader.start()

    def _on_image_downloaded(self, platform_name: str, pixmap: QPixmap, metadata: dict):
        """Handle a downloaded image.

        Args:
            platform_name: Platform name
            pixmap: Downloaded image
            metadata: Image metadata
        """
        # Update the image item with the real image
        if "url" in metadata and metadata["url"] in self.image_items:
            image_item = self.image_items[metadata["url"]]
            image_item.pixmap = pixmap
            image_item.image_label.setPixmap(pixmap)

            # If this is our selected image, update the preview too
            if self.selected_metadata and self.selected_metadata.get("url") == metadata.get("url"):
                self.selected_image = pixmap
                self.preview_image.setPixmap(pixmap)

    def _on_download_progress(self, current: int, total: int):
        """Update the progress bar.

        Args:
            current: Current progress
            total: Total items to process
        """
        progress_percent = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(progress_percent)

        # Hide progress bar when complete
        if current >= total:
            self.progress_bar.setVisible(False)

    def _get_platform_pixmap(self, platform_name: str, width: int, height: int) -> QPixmap:
        """Get a pixmap for the platform (using platform icons as placeholders).

        Args:
            platform_name: Platform name
            width: Desired width
            height: Desired height

        Returns:
            QPixmap with the platform icon
        """
        try:
            # Try to load platform icon
            icon_path = str(get_resource_path(f"icons/1x/{platform_name}.png"))
            pixmap = QPixmap(icon_path)

            if pixmap.isNull():
                # Create placeholder
                pixmap = QPixmap(width, height)
                pixmap.fill(Qt.GlobalColor.darkGray)

            # Scale to desired size
            return pixmap.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatio)
        except Exception:
            # Create placeholder
            pixmap = QPixmap(width, height)
            pixmap.fill(Qt.GlobalColor.darkGray)
            return pixmap

    def _on_image_selected(self, pixmap: QPixmap, metadata: dict):
        """Handle image selection.

        Args:
            pixmap: Selected image pixmap
            metadata: Image metadata
        """
        # Update selected image
        self.selected_image = pixmap
        self.selected_metadata = metadata

        # Update preview
        self.preview_image.setPixmap(pixmap)

        # Enable OK button
        self.ok_button.setEnabled(True)

        # Update selection state of all image items
        for i in range(self.images_layout.count()):
            item = self.images_layout.itemAt(i).widget()
            if isinstance(item, CoverImageItem):
                # Check if this is the selected item by comparing metadata
                is_selected = item.metadata == metadata
                item.setSelected(is_selected)

    def get_selected_image_data(self) -> tuple[QPixmap, dict] | None:
        """Get the selected image data.

        Returns:
            Tuple of (pixmap, metadata) or None if no selection
        """
        if self.selected_image and self.selected_metadata:
            return (self.selected_image, self.selected_metadata)
        return None
