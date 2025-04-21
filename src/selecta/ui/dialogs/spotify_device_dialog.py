"""Component to display Spotify available devices and select current device."""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from selecta.core.utils.audio_player import SpotifyAudioPlayer


class SpotifyDeviceDialog(QDialog):
    """Dialog for selecting a Spotify device."""

    device_selected = pyqtSignal(str)

    def __init__(self, spotify_player: SpotifyAudioPlayer, parent=None):
        """Initialize the Spotify device dialog.

        Args:
            spotify_player: The Spotify audio player
            parent: Parent widget
        """
        super().__init__(parent)
        self.spotify_player = spotify_player
        self.setWindowTitle("Select Spotify Device")
        self.resize(400, 200)

        # Main layout
        layout = QVBoxLayout(self)

        # Instructions
        instructions = QLabel("Select a Spotify device for playback:")
        layout.addWidget(instructions)

        # Device combo box
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(300)
        layout.addWidget(self.device_combo)

        # Current device display
        current_device_layout = QHBoxLayout()
        current_device_layout.addWidget(QLabel("Current device:"))
        self.current_device_label = QLabel("None")
        current_device_layout.addWidget(self.current_device_label)
        layout.addLayout(current_device_layout)

        # Refresh button
        refresh_button = QPushButton("Refresh Devices")
        refresh_button.clicked.connect(self.refresh_devices)
        layout.addWidget(refresh_button)

        # Buttons
        button_layout = QHBoxLayout()
        self.select_button = QPushButton("Select")
        self.select_button.clicked.connect(self.select_device)
        button_layout.addWidget(self.select_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        # Populate devices
        self.refresh_devices()

    def refresh_devices(self):
        """Refresh the list of available Spotify devices."""
        self.device_combo.clear()

        # Get devices from Spotify API
        devices = self.spotify_player.get_available_devices()

        if not devices:
            self.device_combo.addItem("No devices available")
            self.select_button.setEnabled(False)
            return

        # Store device information
        self.devices = devices

        # Add devices to combo box
        for i, device in enumerate(devices):
            # Mark active device with an asterisk
            device_name = f"{device['name']} ({device['type']})"
            if device.get("is_active", False):
                device_name += " *"

            self.device_combo.addItem(device_name)

            # If this is the current device in player, select it
            if self.spotify_player.current_device_id == device["id"]:
                self.device_combo.setCurrentIndex(i)
                self.current_device_label.setText(device_name)

        self.select_button.setEnabled(True)

    def select_device(self):
        """Select the chosen device and emit the device_selected signal."""
        if not self.devices:
            self.reject()
            return

        current_index = self.device_combo.currentIndex()
        if current_index >= 0 and current_index < len(self.devices):
            device = self.devices[current_index]
            self.device_selected.emit(device["id"])
            self.accept()
