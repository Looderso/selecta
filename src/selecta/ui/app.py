import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from selecta.ui.components.navigation_bar import NavigationBar
from selecta.ui.components.side_drawer import SideDrawer
from selecta.ui.themes.theme_manager import Theme, ThemeManager


class SelectaMainWindow(QMainWindow):
    """Main application window for Selecta."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        self.setWindowTitle("Selecta")
        # Set a reasonable minimum size but don't constrain maximum
        self.setMinimumSize(800, 600)

        # Resize to fill available screen space
        self.resize_to_available_screen()

        # Setup central widget and main layout
        self.central_widget = QWidget()
        self.central_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Create the navigation bar
        self.nav_bar = NavigationBar(self)
        self.main_layout.addWidget(self.nav_bar)

        # Create the content layout (below navigation bar)
        self.content_widget = QWidget()
        self.content_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(10)
        self.main_layout.addWidget(self.content_widget, 1)  # 1 = stretch factor

        # Create the main splitter for left and right sides
        self.horizontal_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.horizontal_splitter.setHandleWidth(2)
        self.horizontal_splitter.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.content_layout.addWidget(self.horizontal_splitter)

        # Left side - Contains playlist on top and empty space at bottom
        self.left_widget = QWidget()
        self.left_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.left_layout = QVBoxLayout(self.left_widget)
        self.left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_layout.setSpacing(10)

        # Create vertical splitter for playlist and bottom component
        self.vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        self.vertical_splitter.setHandleWidth(2)
        self.vertical_splitter.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.left_layout.addWidget(self.vertical_splitter)

        # Top component for playlist
        self.playlist_container = QWidget()
        self.playlist_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.playlist_layout = QVBoxLayout(self.playlist_container)
        self.playlist_layout.setContentsMargins(0, 0, 0, 0)

        # Bottom component (empty for now)
        self.bottom_container = QWidget()
        self.bottom_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.bottom_layout = QVBoxLayout(self.bottom_container)
        self.bottom_layout.setContentsMargins(0, 0, 0, 0)

        # Add both to vertical splitter
        self.vertical_splitter.addWidget(self.playlist_container)
        self.vertical_splitter.addWidget(self.bottom_container)

        # Set initial sizes for vertical splitter (90% for playlist, 10% for bottom)
        self.vertical_splitter.setSizes([900, 100])  # Proportional values (9:1 ratio)

        # Right side - For adaptive content
        self.right_container = QWidget()
        self.right_container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)

        # Add left and right to horizontal splitter
        self.horizontal_splitter.addWidget(self.left_widget)
        self.horizontal_splitter.addWidget(self.right_container)

        # Set initial sizes for horizontal splitter (3/4 for left, 1/4 for right)
        self.horizontal_splitter.setSizes([750, 250])  # Proportional values (3:1 ratio)

        # Create the side drawer
        self.side_drawer = SideDrawer(self)
        self.side_drawer.hide()  # Hidden by default

        # Connect signals
        self.nav_bar.settings_button_clicked.connect(self.toggle_side_drawer)
        self.nav_bar.playlists_button_clicked.connect(self.show_playlists)
        self.nav_bar.tracks_button_clicked.connect(self.show_tracks)
        self.nav_bar.vinyl_button_clicked.connect(self.show_vinyl)

    def resize_to_available_screen(self):
        """Resize the window to fill the available screen space."""
        # Get the primary screen
        screen = QApplication.primaryScreen()
        if screen:
            # Get the available geometry (this accounts for taskbars, docks, etc.)
            available_geometry = screen.availableGeometry()

            # Set the window size to match the available screen space
            self.setGeometry(available_geometry)

    def resizeEvent(self, event):
        """Handle resize events to maintain splitter proportions."""
        super().resizeEvent(event)

        # Update splitter sizes when the window is resized
        if hasattr(self, "horizontal_splitter") and hasattr(self, "vertical_splitter"):
            # Maintain the 3:1 horizontal ratio
            total_width = self.horizontal_splitter.width()
            left_width = int(total_width * 0.75)  # 75% for left side
            right_width = total_width - left_width  # 25% for right side
            self.horizontal_splitter.setSizes([left_width, right_width])

            # For vertical splitter, prioritize the playlist section by giving it more space
            total_height = self.vertical_splitter.height()
            top_height = int(total_height * 0.9)  # 90% for top section
            bottom_height = total_height - top_height  # 10% for bottom section
            self.vertical_splitter.setSizes([top_height, bottom_height])

    def toggle_side_drawer(self):
        """Toggle the visibility of the side drawer."""
        if self.side_drawer.isVisible():
            self.side_drawer.hide_drawer()
        else:
            self.side_drawer.show_drawer()

    def set_playlist_content(self, widget):
        """Set the content widget in the playlist area."""
        # Clear the current content
        self._clear_layout(self.playlist_layout)

        # Add the new content
        self.playlist_layout.addWidget(widget)

    def set_bottom_content(self, widget):
        """Set the content widget in the bottom area."""
        # Clear the current content
        self._clear_layout(self.bottom_layout)

        # Add the new content
        self.bottom_layout.addWidget(widget)

    def set_right_content(self, widget):
        """Set the content widget in the right area."""
        # Clear the current content
        self._clear_layout(self.right_layout)

        # Add the new content
        self.right_layout.addWidget(widget)

    def _clear_layout(self, layout):
        """Clear all widgets from a layout."""
        if layout is None:
            return

        # Remove all widgets from the layout
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def show_playlists(self):
        """Show playlists content."""
        from selecta.ui.components.bottom_content import BottomContent
        from selecta.ui.components.playlist_content import PlaylistContent

        # Create playlist content
        playlist_content = PlaylistContent()
        self.set_playlist_content(playlist_content)

        # Create bottom content
        bottom_content = BottomContent()
        self.set_bottom_content(bottom_content)

        # Store a reference to the details panel for switching later
        if hasattr(playlist_content, "playlist_component") and hasattr(
            playlist_content.playlist_component, "details_panel"
        ):
            self.track_details_panel = playlist_content.playlist_component.details_panel

        # Show Spotify search panel by default
        self.show_spotify_search()

    def show_spotify_search(self, initial_search=None):
        """Show Spotify search panel in the right area.

        Args:
            initial_search: Optional initial search query
        """
        from selecta.ui.components.spotify.spotify_search_panel import SpotifySearchPanel

        # Create a new Spotify search panel
        spotify_search_panel = SpotifySearchPanel()
        spotify_search_panel.setObjectName(
            "spotifySearchPanel"
        )  # Add this to make it easier to find

        # Set the initial search if provided
        if initial_search:
            spotify_search_panel.search_bar.set_search_text(initial_search)
            spotify_search_panel._on_search(initial_search)

        self.set_right_content(spotify_search_panel)

    def show_tracks(self):
        """Show tracks content."""
        from selecta.ui.components.bottom_content import BottomContent
        from selecta.ui.components.main_content import MainContent

        # Add main content to playlist area for now
        self.set_playlist_content(MainContent())

        # Add bottom content
        bottom_content = BottomContent()
        self.set_bottom_content(bottom_content)

        # Clear right side
        empty_widget = QWidget()
        self.set_right_content(empty_widget)

    def show_vinyl(self):
        """Show vinyl content."""
        from selecta.ui.components.bottom_content import BottomContent
        from selecta.ui.components.main_content import MainContent

        # Add main content to playlist area for now
        self.set_playlist_content(MainContent())

        # Add bottom content
        bottom_content = BottomContent()
        self.set_bottom_content(bottom_content)

        # Clear right side
        empty_widget = QWidget()
        self.set_right_content(empty_widget)


def run_app():
    """Run the PyQt application."""
    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("Selecta")
    app.setOrganizationName("Looderso")

    # Apply theming
    ThemeManager.apply_theme(app, Theme.DARK)

    # Create and show the main window
    window = SelectaMainWindow()

    # Initial setup - Load playlist view
    window.show_playlists()

    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(run_app())
