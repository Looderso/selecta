# src/selecta/ui/components/playlist/playlist_item.py
from abc import ABC, abstractmethod
from typing import Any

from PyQt6.QtGui import QIcon


class PlaylistItem(ABC):
    """Base class for items in the playlist tree view."""

    def __init__(self, name: str, item_id: Any, parent_id: Any | None = None):
        """Initialize a playlist item.

        Args:
            name: The display name of the item
            item_id: The unique identifier for the item
            parent_id: The parent item's ID, if any
        """
        self.name = name
        self.item_id = item_id
        self.parent_id = parent_id
        self.children: list[PlaylistItem] = []

    @abstractmethod
    def get_icon(self) -> QIcon:
        """Get the icon for this item.

        Returns:
            QIcon appropriate for this type of item
        """
        pass

    @abstractmethod
    def is_folder(self) -> bool:
        """Check if this item is a folder.

        Returns:
            True if this is a folder, False if it's a playlist
        """
        pass

    def add_child(self, child: "PlaylistItem") -> None:
        """Add a child item to this item.

        Args:
            child: The child item to add
        """
        self.children.append(child)

    def remove_child(self, child: "PlaylistItem") -> bool:
        """Remove a child item from this item.

        Args:
            child: The child item to remove

        Returns:
            True if the child was found and removed, False otherwise
        """
        if child in self.children:
            self.children.remove(child)
            return True
        return False
