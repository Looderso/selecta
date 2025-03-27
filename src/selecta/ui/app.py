import sys

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

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
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Create the navigation bar
        self.nav_bar = NavigationBar(self)
        self.main_layout.addWidget(self.nav_bar)

        # Create the content area
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.addWidget(self.content_area, 1)  # 1 = stretch factor

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

    def toggle_side_drawer(self):
        """Toggle the visibility of the side drawer."""
        if self.side_drawer.isVisible():
            self.side_drawer.hide_drawer()
        else:
            self.side_drawer.show_drawer()

    def set_content(self, widget):
        """Set the content widget in the main area."""
        # Clear the current content
        for i in reversed(range(self.content_layout.count())):
            item = self.content_layout.itemAt(i)

            if item:
                widget_item = item.widget()
                if widget_item:
                    widget_item.deleteLater()

        # Add the new content
        self.content_layout.addWidget(widget)

    def show_playlists(self):
        """Show playlists content."""
        from selecta.ui.components.playlist_content import PlaylistContent

        self.set_content(PlaylistContent())

    def show_tracks(self):
        """Show tracks content."""
        # For now, just show the main content
        from selecta.ui.components.main_content import MainContent

        self.set_content(MainContent())

    def show_vinyl(self):
        """Show vinyl content."""
        # For now, just show the main content
        from selecta.ui.components.main_content import MainContent

        self.set_content(MainContent())


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

    # Add main content initially
    from selecta.ui.components.main_content import MainContent

    window.set_content(MainContent())

    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(run_app())
