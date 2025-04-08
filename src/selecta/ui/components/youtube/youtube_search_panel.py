"""YouTube search panel for the UI."""

from typing import cast

from loguru import logger
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
)

from selecta.core.platform.platform_factory import PlatformFactory
from selecta.core.platform.youtube.client import YouTubeClient
from selecta.ui.components.loading_widget import LoadableWidget
from selecta.ui.components.playlist.youtube.youtube_track_item import YouTubeTrackItem


class YouTubeSearchPanel(LoadableWidget):
    """Panel for searching and displaying YouTube videos."""

    # Signal emitted when a video is selected
    video_selected = pyqtSignal(YouTubeTrackItem)

    def __init__(self, parent=None):
        """Initialize the YouTube search panel.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.youtube_client = cast(YouTubeClient, PlatformFactory.create("youtube"))
        self.search_results = []
        self._setup_ui()

    def _setup_ui(self):
        """Set up the search panel UI."""
        main_layout = QVBoxLayout(self)

        # Status/header section
        header_layout = QHBoxLayout()
        self.status_label = QLabel("YouTube Search")
        header_layout.addWidget(self.status_label)

        # Auth button
        self.auth_button = QPushButton("Connect to YouTube")
        self.auth_button.clicked.connect(self._authenticate)
        header_layout.addWidget(self.auth_button)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # Search results table
        self.results_table = QTableView()
        self.results_table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.doubleClicked.connect(self._on_result_double_clicked)
        main_layout.addWidget(self.results_table)

        # Button row
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.add_button = QPushButton("Add to Playlist")
        self.add_button.setEnabled(False)
        self.add_button.clicked.connect(self._on_add_clicked)
        button_layout.addWidget(self.add_button)

        main_layout.addLayout(button_layout)

        # Set up loading functionality
        self._create_loading_widget("Ready to search YouTube...")
        self.hide_loading()
        
        # Update the auth status
        self._update_auth_status()

    def _update_auth_status(self):
        """Update the authentication status display."""
        if self.youtube_client and self.youtube_client.is_authenticated():
            self.status_label.setText("Connected to YouTube")
            self.auth_button.setText("Reconnect")
            self.auth_button.setToolTip("Reconnect to YouTube")
        else:
            self.status_label.setText("Not connected to YouTube")
            self.auth_button.setText("Connect to YouTube")
            self.auth_button.setToolTip("Connect to YouTube to search videos")

    def _authenticate(self):
        """Authenticate with YouTube."""
        if not self.youtube_client:
            self.youtube_client = cast(YouTubeClient, PlatformFactory.create("youtube"))
            if not self.youtube_client:
                QMessageBox.critical(self, "Error", "Failed to create YouTube client")
                return

        try:
            # Show loading widget during authentication
            self.show_loading("Connecting to YouTube...")

            # Process events to ensure loading widget is displayed
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()

            # Authenticate
            result = self.youtube_client.authenticate()

            # Hide loading widget
            self.hide_loading()

            if result:
                QMessageBox.information(
                    self, "Authentication Successful", "Successfully connected to YouTube!"
                )
                self._update_auth_status()
            else:
                QMessageBox.warning(
                    self, "Authentication Failed", "Failed to connect to YouTube. Please try again."
                )
        except Exception as e:
            self.hide_loading()
            logger.exception(f"Error authenticating with YouTube: {e}")
            QMessageBox.critical(self, "Authentication Error", f"Error: {str(e)}")

    def search(self, query, limit=20):
        """Search for videos on YouTube.

        Args:
            query: Search query string
            limit: Maximum number of results to return
        """
        if not self.youtube_client or not self.youtube_client.is_authenticated():
            QMessageBox.warning(
                self, "Not Connected", "Please connect to YouTube first"
            )
            return

        try:
            # Show loading widget during search
            self.show_loading(f"Searching YouTube for '{query}'...")

            # Process events to ensure loading widget is displayed
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()

            # Perform search
            self.search_results = self.youtube_client.search_tracks(query, limit=limit)

            # Create a model for the results table
            from PyQt6.QtGui import QStandardItem, QStandardItemModel

            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(["Title", "Channel", "Duration"])

            # Add results to model
            for result in self.search_results:
                # Extract video info
                snippet = result.get("snippet", {})
                title = snippet.get("title", "")
                channel = snippet.get("channelTitle", "")
                
                # Get duration if available
                duration_str = "N/A"
                if "contentDetails" in result and "duration" in result["contentDetails"]:
                    from selecta.core.platform.youtube.models import _parse_iso8601_duration
                    duration_seconds = _parse_iso8601_duration(result["contentDetails"]["duration"])
                    if duration_seconds:
                        minutes, seconds = divmod(duration_seconds, 60)
                        duration_str = f"{minutes}:{seconds:02d}"
                
                # Create row
                title_item = QStandardItem(title)
                channel_item = QStandardItem(channel)
                duration_item = QStandardItem(duration_str)
                
                model.appendRow([title_item, channel_item, duration_item])
            
            # Set model to table
            self.results_table.setModel(model)
            self.results_table.resizeColumnsToContents()
            
            # Update status
            count = len(self.search_results)
            self.status_label.setText(f"Found {count} results for '{query}'")
            
            # Enable/disable add button
            self.add_button.setEnabled(count > 0)
            
            # Hide loading widget
            self.hide_loading()
            
        except Exception as e:
            self.hide_loading()
            logger.exception(f"Error searching YouTube: {e}")
            QMessageBox.critical(self, "Search Error", f"Error: {str(e)}")

    def _on_result_double_clicked(self, index):
        """Handle double-click on a search result.

        Args:
            index: Model index that was double-clicked
        """
        if index.isValid():
            self._select_current_result()

    def _on_add_clicked(self):
        """Handle click on the Add button."""
        self._select_current_result()

    def _select_current_result(self):
        """Select the currently highlighted search result."""
        if not self.results_table.selectionModel().hasSelection():
            return
            
        index = self.results_table.selectionModel().currentIndex()
        if not index.isValid():
            return
            
        row = index.row()
        if 0 <= row < len(self.search_results):
            result = self.search_results[row]
            
            # Extract video info
            video_id = result.get("id", {}).get("videoId", "")
            if not video_id:
                return
                
            snippet = result.get("snippet", {})
            title = snippet.get("title", "")
            channel = snippet.get("channelTitle", "")
            
            # Get duration if available
            duration_seconds = 0
            if "contentDetails" in result and "duration" in result["contentDetails"]:
                from selecta.core.platform.youtube.models import _parse_iso8601_duration
                duration_str = result["contentDetails"]["duration"]
                duration_seconds = _parse_iso8601_duration(duration_str) or 0
            
            # Get thumbnail URL
            thumbnail_url = None
            if "thumbnails" in snippet:
                thumbnails = snippet["thumbnails"]
                for size in ["high", "medium", "default"]:
                    if size in thumbnails and "url" in thumbnails[size]:
                        thumbnail_url = thumbnails[size]["url"]
                        break
            
            # Create a track item
            track_item = YouTubeTrackItem(
                id=video_id,
                title=title,
                artist=channel,
                duration=duration_seconds,
                thumbnail_url=thumbnail_url,
            )
            
            # Emit signal
            self.video_selected.emit(track_item)