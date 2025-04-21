# src/selecta/ui/widgets/search_bar.py
from collections.abc import Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import (
    QCompleter,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)


class SearchBar(QWidget):
    """Search bar component with auto-completion support."""

    # Signal emitted when search is confirmed (by pressing Enter)
    search_confirmed = pyqtSignal(str)

    # Signal emitted when a completer item is activated
    completer_activated = pyqtSignal(str)

    # Signal emitted when a completer item is highlighted (arrow keys)
    completer_highlighted = pyqtSignal(str)

    def __init__(
        self,
        placeholder_text: str = "Search...",
        completion_items: list[str] | None = None,
        parent: QWidget | None = None,
    ):
        """Initialize the search bar.

        Args:
            placeholder_text: Text to display when search bar is empty
            completion_items: Optional list of strings for auto-completion
            parent: Parent widget
        """
        super().__init__(parent)
        self.setObjectName("searchBar")
        self._suppress_text_changed = False

        # Create the layout
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Create the search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(placeholder_text)
        self.search_input.setObjectName("searchInput")
        self.search_input.returnPressed.connect(self._on_search_confirmed)

        # Style the search input
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border-radius: 4px;
                border: 1px solid #444;
                background-color: #333;
                color: white;
            }

            QLineEdit:focus {
                border: 1px solid #3498db;
            }
        """)

        # Create search button
        self.search_button = QPushButton("Search")
        self.search_button.setObjectName("searchButton")
        self.search_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_button.clicked.connect(self._on_search_confirmed)

        # Set button style
        self.search_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                background-color: #3498db;
                color: white;
            }

            QPushButton:hover {
                background-color: #2980b9;
            }

            QPushButton:pressed {
                background-color: #1f6aa5;
            }
        """)

        # Add widgets to layout
        self.main_layout.addWidget(self.search_input, 1)  # 1 = stretch factor
        self.main_layout.addWidget(self.search_button)

        # Initialize completer and model
        self.completer = None
        self.completer_model = None
        self.completion_items = []
        self.current_text = ""

        # Set initial completion items
        self.set_completion_items(completion_items)

        # Setup completer key handling
        self.search_input.textChanged.connect(self._on_text_changed)

    def set_completion_items(self, items: list[str] | None) -> None:
        """Set or update auto-completion items.

        Args:
            items: List of strings for auto-completion, or None to disable
        """
        if items:
            # Store the original items
            self.completion_items = items.copy()

            # Create a new model for the completer
            self.completer_model = QStandardItemModel()

            # Add items to the model
            for item in items:
                self.completer_model.appendRow(QStandardItem(item))

            # Create completer with the model
            self.completer = QCompleter(self.completer_model, self)
            self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
            self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)

            # Connect signals
            self.completer.activated.connect(self._on_completion_selected)
            self.completer.highlighted.connect(self._on_completion_highlighted)

            self.search_input.setCompleter(self.completer)
        else:
            self.completion_items = []
            self.completer_model = None
            self.completer = None
            self.search_input.setCompleter(None)

    def get_search_text(self) -> str:
        """Get the current search text.

        Returns:
            Current search text
        """
        return self.search_input.text()

    def set_search_text(self, text: str) -> None:
        """Set the search text.

        Args:
            text: Text to set in the search bar
        """
        self._suppress_text_changed = True
        self.search_input.setText(text)
        self._suppress_text_changed = False

    def clear(self) -> None:
        """Clear the search text."""
        self.search_input.clear()

    def set_focus(self) -> None:
        """Set focus to the search input."""
        self.search_input.setFocus()

    def set_on_search_callback(self, callback: Callable[[str], None]) -> None:
        """Set a callback function for when search is confirmed.

        Args:
            callback: Function to call when search is confirmed
        """
        self.search_confirmed.connect(callback)

    def _on_search_confirmed(self) -> None:
        """Handle search confirmation (Enter key or button click)."""
        search_text = self.get_search_text()
        self.search_confirmed.emit(search_text)

    def _on_completion_selected(self, text: str) -> None:
        """Handle selection of an auto-completion item.

        Args:
            text: Selected completion text
        """
        # Skip the "No results" item which is not selectable
        if text == "No results":
            return

        self.set_search_text(text)
        self.completer_activated.emit(text)

    def _on_completion_highlighted(self, text: str) -> None:
        """Handle highlighting of an auto-completion item.

        Args:
            text: Highlighted completion text
        """
        # Skip the "No results" item which is not selectable
        if text == "No results":
            return

        # Only store the highlighted text without changing the input
        # This prevents the popup from closing when navigating with arrow keys
        self.completer_highlighted.emit(text)

    def _on_text_changed(self, text: str) -> None:
        """Handle text changes to update completer.

        Args:
            text: Current search text
        """
        if self._suppress_text_changed:
            return

        if not self.completer or not self.completer_model or not self.completion_items:
            return

        # Save current text
        self.current_text = text

        # Clear the current model
        self.completer_model.clear()

        # Filter items based on text
        if text:
            text_lower = text.lower()
            filtered_items = [item for item in self.completion_items if text_lower in item.lower()]

            # If no matches, show "No results"
            if not filtered_items:
                self.completer_model.appendRow(QStandardItem("No results"))
            else:
                # Add filtered items to model
                for item in filtered_items:
                    self.completer_model.appendRow(QStandardItem(item))
        else:
            # If empty, show all items
            for item in self.completion_items:
                self.completer_model.appendRow(QStandardItem(item))
