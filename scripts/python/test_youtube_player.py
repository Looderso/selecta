"""Test script for the YouTube audio player functionality."""

import sys
from pathlib import Path

from loguru import logger
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from selecta.core.platform.youtube.models import YouTubeVideo
from selecta.ui.components.player.audio_player_component import AudioPlayerComponent


class TestWindow(QMainWindow):
    """Test window for the YouTube audio player."""

    def __init__(self):
        """Initialize the test window."""
        super().__init__()
        self.setWindowTitle("YouTube Player Test")
        self.setGeometry(100, 100, 800, 200)

        # Create central widget and layout
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        # Create the audio player component
        self.player = AudioPlayerComponent()
        layout.addWidget(self.player)

        # Set central widget
        self.setCentralWidget(central_widget)

        # Schedule loading a test YouTube video after the UI is shown
        QTimer.singleShot(1000, self.load_test_video)

    def load_test_video(self):
        """Load a test YouTube video for playback."""
        # Create a simple YouTube video object for testing
        # This is Rick Astley's "Never Gonna Give You Up" - a classic test video
        video_id = "dQw4w9WgXcQ"

        logger.info(f"Loading test YouTube video: {video_id}")

        # Create a YouTube video object with the necessary attributes
        test_video = YouTubeVideo(
            id=video_id,
            title="Test YouTube Video",
            channel_id="test_channel",
            channel_title="Test Channel",
            description="Test description",
            duration_seconds=210,  # 3:30
        )

        # Load the video in the player
        self.player.load_track(test_video)


def main():
    """Run the test application."""
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
