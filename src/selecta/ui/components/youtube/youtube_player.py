"""YouTube video player window."""

from loguru import logger
from PyQt6.QtCore import QCoreApplication, QSize, Qt, QUrl
from PyQt6.QtGui import QIcon

# Set WebEngine flags before any QApplication is created
# This must be done before importing QWebEngineView
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

# Now import WebEngine
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget


class YouTubePlayerWindow(QMainWindow):
    """Simple YouTube player window displaying YouTube videos in a web view."""

    def __init__(self, parent=None) -> None:
        """Initialize the YouTube player window.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.setWindowTitle("YouTube Player")
        self.setGeometry(100, 100, 800, 600)
        self.setMinimumSize(QSize(640, 480))

        # Set window icon if available
        try:
            from selecta.core.utils.path_helper import get_resources_path

            icon_path = get_resources_path() / "icons" / "1x" / "youtube.png"
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
        except Exception as e:
            logger.warning(f"Could not set YouTube player window icon: {e}")

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create web engine view
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)

        # Store the current video ID
        self.current_video_id = None

    def load_video(self, video_id: str) -> None:
        """Load a YouTube video by its ID.

        Args:
            video_id: YouTube video ID
        """
        if not video_id:
            logger.warning("No YouTube video ID provided")
            return

        self.current_video_id = video_id
        self.setWindowTitle(f"YouTube Player - {video_id}")

        # Set the YouTube embed URL with autoplay enabled
        embed_url = f"https://www.youtube.com/embed/{video_id}?autoplay=1"
        logger.info(f"Loading YouTube video: {embed_url}")

        # Load video
        self.web_view.setUrl(QUrl(embed_url))

    def closeEvent(self, event) -> None:
        """Handle window close event.

        Args:
            event: Close event
        """
        # Stop video playback when the window is closed
        self.web_view.setUrl(QUrl("about:blank"))
        event.accept()


def create_youtube_player_window(video_id: str, parent=None) -> YouTubePlayerWindow:
    """Create and show a YouTube player window.

    Args:
        video_id: YouTube video ID to play
        parent: Parent widget

    Returns:
        The created YouTube player window
    """
    window = YouTubePlayerWindow(parent)
    window.load_video(video_id)
    window.show()
    return window
