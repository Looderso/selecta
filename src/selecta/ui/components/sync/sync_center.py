"""Sync Center component for managing cross-platform synchronization."""

from dataclasses import dataclass
from datetime import datetime

from loguru import logger
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from selecta.core.data.repositories.playlist_repository import PlaylistRepository
from selecta.core.data.repositories.settings_repository import SettingsRepository
from selecta.core.platform.platform_factory import PlatformFactory
from selecta.ui.widgets.loading_widget import LoadableWidget


@dataclass
class SyncedPlaylistInfo:
    """Information about a synchronized playlist."""

    local_playlist_id: int
    local_playlist_name: str
    platform_playlist_id: str
    platform_name: str
    sync_direction: str  # "bidirectional", "import_only", "export_only"
    last_sync_time: datetime | None
    sync_status: str  # "in_sync", "outdated", "failed", "unknown"
    track_count_local: int
    track_count_platform: int | None
    sync_conflicts: list[str]  # List of conflict descriptions


class SyncStatusWorker(QThread):
    """Worker thread for fetching sync status from platforms."""

    status_updated = pyqtSignal(str, list)  # platform_name, synced_playlists
    error_occurred = pyqtSignal(str, str)  # platform_name, error_message

    def __init__(self, platform_name: str, settings_repo: SettingsRepository):
        super().__init__()
        self.platform_name = platform_name
        self.settings_repo = settings_repo
        self.playlist_repo = PlaylistRepository()

    def run(self):
        """Fetch sync status for the platform."""
        try:
            logger.info(f"Fetching sync status for {self.platform_name}")

            # Get platform client
            platform_client = PlatformFactory.create(self.platform_name, self.settings_repo)
            if not platform_client or not platform_client.is_authenticated():
                self.error_occurred.emit(self.platform_name, f"{self.platform_name} not authenticated")
                return

            # Get all local playlists that have platform links
            local_playlists = self.playlist_repo.get_all()
            synced_playlists = []

            for local_playlist in local_playlists:
                # Check if this playlist has platform metadata for our platform
                platform_info = self.playlist_repo.get_platform_info(local_playlist.id, self.platform_name)
                if platform_info:
                    platform_playlist_id = platform_info.platform_id

                    # Get platform track count (this might be slow, but only happens on refresh)
                    platform_track_count = None
                    try:
                        platform_tracks = platform_client.get_playlist_tracks(platform_playlist_id)
                        platform_track_count = len(platform_tracks) if platform_tracks else 0
                    except Exception as e:
                        logger.warning(f"Could not get track count for {platform_playlist_id}: {e}")

                    # Get local track count
                    local_tracks = self.playlist_repo.get_playlist_tracks(local_playlist.id)
                    local_track_count = len(local_tracks) if local_tracks else 0

                    # Determine sync status (simplified for now)
                    sync_status = (
                        "in_sync"
                        if platform_track_count is not None and local_track_count == platform_track_count
                        else "outdated"
                        if platform_track_count is not None
                        else "unknown"
                    )

                    synced_playlist = SyncedPlaylistInfo(
                        local_playlist_id=local_playlist.id,
                        local_playlist_name=local_playlist.name,
                        platform_playlist_id=platform_playlist_id,
                        platform_name=self.platform_name,
                        sync_direction="bidirectional",  # Default for now
                        last_sync_time=platform_info.last_linked,
                        sync_status=sync_status,
                        track_count_local=local_track_count,
                        track_count_platform=platform_track_count,
                        sync_conflicts=[],  # TODO: Implement conflict detection
                    )
                    synced_playlists.append(synced_playlist)

            self.status_updated.emit(self.platform_name, synced_playlists)

        except Exception as e:
            logger.exception(f"Error fetching sync status for {self.platform_name}")
            self.error_occurred.emit(self.platform_name, str(e))


class SyncOverviewWidget(QWidget):
    """Overview widget showing sync statistics and refresh button."""

    refresh_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._total_synced = 0
        self._last_refresh = None

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Overview stats
        self.stats_label = QLabel("📊 Loading sync overview...")
        layout.addWidget(self.stats_label)

        layout.addStretch(1)

        # Refresh button
        self.refresh_button = QPushButton("🔄 Refresh Status")
        self.refresh_button.clicked.connect(self.refresh_requested.emit)
        layout.addWidget(self.refresh_button)

    def update_stats(self, total_synced: int, last_refresh: datetime | None = None):
        """Update the overview statistics."""
        self._total_synced = total_synced
        self._last_refresh = last_refresh or datetime.now()

        last_refresh_str = "just now"
        if self._last_refresh:
            time_diff = datetime.now() - self._last_refresh
            if time_diff.total_seconds() < 60:
                last_refresh_str = "just now"
            elif time_diff.total_seconds() < 3600:
                minutes = int(time_diff.total_seconds() / 60)
                last_refresh_str = f"{minutes} minutes ago"
            else:
                hours = int(time_diff.total_seconds() / 3600)
                last_refresh_str = f"{hours} hours ago"

        self.stats_label.setText(
            f"📊 {self._total_synced} synced playlists across platforms • " f"Last refresh: {last_refresh_str}"
        )

    def set_refreshing(self, refreshing: bool):
        """Update UI to show refresh state."""
        self.refresh_button.setEnabled(not refreshing)
        if refreshing:
            self.refresh_button.setText("🔄 Refreshing...")
        else:
            self.refresh_button.setText("🔄 Refresh Status")


class SyncedPlaylistListWidget(QTableWidget):
    """Widget for displaying and managing synced playlists."""

    sync_requested = pyqtSignal(list)  # List of selected playlist info

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._synced_playlists: list[SyncedPlaylistInfo] = []

    def _setup_ui(self):
        """Set up the table widget."""
        # Set up columns
        headers = ["Select", "Playlist", "Platform", "Direction", "Status", "Tracks", "Last Sync"]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)

        # Configure table appearance
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSortingEnabled(True)

        # Resize columns
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Select
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Playlist
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Platform
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Direction
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Tracks
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Last Sync

    def update_playlists(self, synced_playlists: list[SyncedPlaylistInfo]):
        """Update the playlist list."""
        self._synced_playlists = synced_playlists
        self.setRowCount(len(synced_playlists))

        for row, playlist_info in enumerate(synced_playlists):
            # Select checkbox
            checkbox = QCheckBox()
            self.setCellWidget(row, 0, checkbox)

            # Playlist name
            name_item = QTableWidgetItem(playlist_info.local_playlist_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.setItem(row, 1, name_item)

            # Platform with icon
            platform_text = f"{playlist_info.platform_name.title()}"
            platform_item = QTableWidgetItem(platform_text)
            platform_item.setFlags(platform_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.setItem(row, 2, platform_item)

            # Direction
            direction_map = {"bidirectional": "↔", "import_only": "←", "export_only": "→"}
            direction_icon = direction_map.get(playlist_info.sync_direction, "?")
            direction_label = playlist_info.sync_direction.replace("_", " ").title()
            direction_text = f"{direction_icon} {direction_label}"
            direction_item = QTableWidgetItem(direction_text)
            direction_item.setFlags(direction_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.setItem(row, 3, direction_item)

            # Status with icon
            status_map = {
                "in_sync": "✅ In Sync",
                "outdated": "⚠️ Outdated",
                "failed": "❌ Failed",
                "unknown": "❓ Unknown",
            }
            status_text = status_map.get(playlist_info.sync_status, "❓ Unknown")
            status_item = QTableWidgetItem(status_text)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Color code the status
            if playlist_info.sync_status == "in_sync":
                status_item.setBackground(Qt.GlobalColor.green)
            elif playlist_info.sync_status == "outdated":
                status_item.setBackground(Qt.GlobalColor.yellow)
            elif playlist_info.sync_status == "failed":
                status_item.setBackground(Qt.GlobalColor.red)

            self.setItem(row, 4, status_item)

            # Track counts
            platform_count = playlist_info.track_count_platform
            platform_count_str = str(platform_count) if platform_count is not None else "?"
            track_text = f"{playlist_info.track_count_local}/{platform_count_str}"
            track_item = QTableWidgetItem(track_text)
            track_item.setFlags(track_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.setItem(row, 5, track_item)

            # Last sync time
            last_sync_text = "Never"
            if playlist_info.last_sync_time:
                time_diff = datetime.now() - playlist_info.last_sync_time
                if time_diff.total_seconds() < 3600:
                    minutes = int(time_diff.total_seconds() / 60)
                    last_sync_text = f"{minutes}m ago"
                elif time_diff.total_seconds() < 86400:
                    hours = int(time_diff.total_seconds() / 3600)
                    last_sync_text = f"{hours}h ago"
                else:
                    days = int(time_diff.total_seconds() / 86400)
                    last_sync_text = f"{days}d ago"

            last_sync_item = QTableWidgetItem(last_sync_text)
            last_sync_item.setFlags(last_sync_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.setItem(row, 6, last_sync_item)

    def get_selected_playlists(self) -> list[SyncedPlaylistInfo]:
        """Get list of selected playlists."""
        selected = []
        for row in range(self.rowCount()):
            checkbox = self.cellWidget(row, 0)
            if checkbox and checkbox.isChecked() and row < len(self._synced_playlists):
                selected.append(self._synced_playlists[row])
        return selected

    def select_all(self, checked: bool):
        """Select or deselect all playlists."""
        for row in range(self.rowCount()):
            checkbox = self.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(checked)


class BulkActionsWidget(QWidget):
    """Widget for bulk sync operations."""

    sync_selected_requested = pyqtSignal()
    preview_selected_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)

        # Select all checkbox
        self.select_all_checkbox = QCheckBox("Select All")
        layout.addWidget(self.select_all_checkbox)

        layout.addStretch(1)

        # Bulk action buttons
        self.preview_button = QPushButton("👁️ Preview Changes")
        self.preview_button.clicked.connect(self.preview_selected_requested.emit)
        layout.addWidget(self.preview_button)

        self.sync_button = QPushButton("⚡ Sync Selected")
        self.sync_button.clicked.connect(self.sync_selected_requested.emit)
        layout.addWidget(self.sync_button)

    def update_selection_count(self, count: int):
        """Update UI based on selection count."""
        enabled = count > 0
        self.preview_button.setEnabled(enabled)
        self.sync_button.setEnabled(enabled)

        if count == 0:
            self.preview_button.setText("👁️ Preview Changes")
            self.sync_button.setText("⚡ Sync Selected")
        else:
            self.preview_button.setText(f"👁️ Preview Changes ({count})")
            self.sync_button.setText(f"⚡ Sync Selected ({count})")


class SyncCenter(LoadableWidget):
    """Main sync center component for managing cross-platform synchronization."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("syncCenter")

        self.settings_repo = SettingsRepository()
        self.playlist_repo = PlaylistRepository()

        # Data
        self._synced_playlists: dict[str, list[SyncedPlaylistInfo]] = {}
        self._workers: dict[str, SyncStatusWorker] = {}

        self._setup_ui()
        self._connect_signals()

        # Load initial data (cached/quick)
        self._load_cached_data()

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Overview section
        self.overview_widget = SyncOverviewWidget()
        layout.addWidget(self.overview_widget)

        # Platform tabs
        self.platform_tabs = QTabWidget()
        self.platform_tabs.currentChanged.connect(self._on_tab_changed)

        # Create tabs for each platform
        self.platform_widgets = {}
        platforms = ["all", "spotify", "rekordbox", "youtube"]

        for platform in platforms:
            tab_widget = QWidget()
            tab_layout = QVBoxLayout(tab_widget)
            tab_layout.setContentsMargins(0, 10, 0, 0)

            # Playlist list
            playlist_list = SyncedPlaylistListWidget()
            tab_layout.addWidget(playlist_list)

            # Bulk actions
            bulk_actions = BulkActionsWidget()
            tab_layout.addWidget(bulk_actions)

            self.platform_widgets[platform] = {
                "widget": tab_widget,
                "playlist_list": playlist_list,
                "bulk_actions": bulk_actions,
            }

            # Add tab
            tab_name = platform.title() if platform != "all" else "All Platforms"
            self.platform_tabs.addTab(tab_widget, tab_name)

        layout.addWidget(self.platform_tabs)

    def _connect_signals(self):
        """Connect widget signals."""
        # Overview
        self.overview_widget.refresh_requested.connect(self.refresh_sync_status)

        # Platform widgets
        for platform, widgets in self.platform_widgets.items():
            playlist_list = widgets["playlist_list"]
            bulk_actions = widgets["bulk_actions"]

            # Connect bulk actions
            bulk_actions.select_all_checkbox.toggled.connect(playlist_list.select_all)
            bulk_actions.sync_selected_requested.connect(
                lambda platform=platform: self._sync_selected_playlists(platform)
            )
            bulk_actions.preview_selected_requested.connect(
                lambda platform=platform: self._preview_selected_playlists(platform)
            )

    def _load_cached_data(self):
        """Load cached sync data quickly."""
        # For now, just show empty state
        # TODO: Implement actual caching
        self.overview_widget.update_stats(0)

        # Update all platform tabs
        for widgets in self.platform_widgets.values():
            widgets["playlist_list"].update_playlists([])
            widgets["bulk_actions"].update_selection_count(0)

    def refresh_sync_status(self):
        """Refresh sync status from all platforms."""
        logger.info("Refreshing sync status...")

        self.overview_widget.set_refreshing(True)

        # Clear previous data
        self._synced_playlists.clear()

        # Stop any existing workers
        for worker in self._workers.values():
            if worker.isRunning():
                worker.quit()
                worker.wait(3000)  # Wait up to 3 seconds
        self._workers.clear()

        # Start workers for each platform
        platforms = ["spotify", "rekordbox", "youtube"]
        for platform in platforms:
            worker = SyncStatusWorker(platform, self.settings_repo)
            worker.status_updated.connect(self._on_status_updated)
            worker.error_occurred.connect(self._on_status_error)
            worker.finished.connect(lambda platform=platform: self._on_worker_finished(platform))

            self._workers[platform] = worker
            worker.start()

    def _on_status_updated(self, platform_name: str, synced_playlists: list[SyncedPlaylistInfo]):
        """Handle sync status update from worker."""
        logger.info(f"Received sync status for {platform_name}: {len(synced_playlists)} playlists")

        self._synced_playlists[platform_name] = synced_playlists
        self._update_ui()

    def _on_status_error(self, platform_name: str, error_message: str):
        """Handle sync status error from worker."""
        logger.error(f"Sync status error for {platform_name}: {error_message}")

        # Show error in UI
        QMessageBox.warning(
            self,
            f"{platform_name.title()} Sync Error",
            f"Could not fetch sync status for {platform_name}:\n{error_message}",
        )

    def _on_worker_finished(self, platform_name: str):
        """Handle worker completion."""
        if platform_name in self._workers:
            del self._workers[platform_name]

        # If all workers are done, update refreshing state
        if not self._workers:
            self.overview_widget.set_refreshing(False)

    def _update_ui(self):
        """Update UI with current sync data."""
        # Calculate total synced playlists
        total_synced = sum(len(playlists) for playlists in self._synced_playlists.values())
        self.overview_widget.update_stats(total_synced)

        # Update platform-specific tabs
        for platform, widgets in self.platform_widgets.items():
            if platform == "all":
                # Combine all platforms
                all_playlists = []
                for platform_playlists in self._synced_playlists.values():
                    all_playlists.extend(platform_playlists)
                widgets["playlist_list"].update_playlists(all_playlists)
            else:
                # Platform-specific
                platform_playlists = self._synced_playlists.get(platform, [])
                widgets["playlist_list"].update_playlists(platform_playlists)

            widgets["bulk_actions"].update_selection_count(0)  # Reset selection

    def _on_tab_changed(self, _index: int):
        """Handle platform tab change."""
        # Could be used for lazy loading if needed
        pass

    def _sync_selected_playlists(self, platform: str):
        """Sync selected playlists."""
        widgets = self.platform_widgets[platform]
        selected = widgets["playlist_list"].get_selected_playlists()

        if not selected:
            QMessageBox.information(self, "No Selection", "Please select playlists to sync.")
            return

        # TODO: Implement actual sync operation
        playlist_names = [p.local_playlist_name for p in selected]
        QMessageBox.information(
            self,
            "Sync Started",
            f"Syncing {len(selected)} playlists:\n"
            + "\n".join(playlist_names[:5])
            + ("..." if len(playlist_names) > 5 else ""),
        )

    def _preview_selected_playlists(self, platform: str):
        """Preview changes for selected playlists."""
        widgets = self.platform_widgets[platform]
        selected = widgets["playlist_list"].get_selected_playlists()

        if not selected:
            QMessageBox.information(self, "No Selection", "Please select playlists to preview.")
            return

        # TODO: Implement preview dialog
        playlist_names = [p.local_playlist_name for p in selected]
        QMessageBox.information(
            self,
            "Preview",
            f"Preview for {len(selected)} playlists:\n"
            + "\n".join(playlist_names[:5])
            + ("..." if len(playlist_names) > 5 else ""),
        )
