from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from selecta.ui.components.platform_auth_panel import PlatformAuthPanel


class SideDrawer(QWidget):
    """Side drawer for settings and authentication."""

    def __init__(self, parent: QWidget):
        """Initialize the side drawer."""
        super().__init__(parent)
        self._parent = parent
        self.setObjectName("sideDrawer")

        # Set fixed width for the drawer
        self.setFixedWidth(350)

        # Set drawer style
        self.setStyleSheet("""
            #sideDrawer {
                background-color: #252525;
                border-left: 1px solid #333333;
            }
            QLabel#drawerTitle {
                font-size: 18px;
                font-weight: bold;
                padding: 20px 0px 10px 0px;
            }
        """)

        # Initialize UI components
        self._setup_ui()

        # Position the drawer initially outside the visible area
        self.setGeometry(self._parent.width(), 0, self.width(), self._parent.height())

        # Set up animation
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.setDuration(250)  # milliseconds

    def _setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header with title
        title_label = QLabel("Settings")
        title_label.setObjectName("drawerTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title_label)

        # Close button
        close_button = QPushButton("×")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 24px;
                color: #AAAAAA;
            }
            QPushButton:hover {
                color: #FFFFFF;
            }
        """)
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(self.hide_drawer)

        # Adjust layout to position close button at the top right
        title_layout = QVBoxLayout()
        title_layout.addWidget(
            close_button, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop
        )
        layout.insertLayout(0, title_layout)

        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Add platform authentication panel
        authentication_label = QLabel("Platform Authentication")
        authentication_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #DDDDDD;")
        scroll_layout.addWidget(authentication_label)

        self.auth_panel = PlatformAuthPanel()
        scroll_layout.addWidget(self.auth_panel)

        # Add additional settings sections as needed
        scroll_layout.addStretch(1)  # Push everything to the top

        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area, 1)  # 1 = stretch factor

    def show_drawer(self):
        """Show the drawer with animation."""
        self.show()

        # Update parent reference size in case the window was resized
        target_x = self._parent.width() - self.width()
        self.animation.setStartValue(
            QRect(self._parent.width(), 0, self.width(), self._parent.height())
        )
        self.animation.setEndValue(QRect(target_x, 0, self.width(), self._parent.height()))
        self.animation.start()

    def hide_drawer(self):
        """Hide the drawer with animation."""
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(
            QRect(self._parent.width(), 0, self.width(), self._parent.height())
        )
        self.animation.start()

        # Hide the drawer after animation finishes
        self.animation.finished.connect(self.hide)
