# src/selecta/ui/components/playlist/playlist_tree_model.py
from typing import Any

from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt

from selecta.ui.components.playlist.playlist_item import PlaylistItem


class PlaylistTreeModel(QAbstractItemModel):
    """Model for displaying playlists in a tree view."""

    def __init__(self, parent=None):
        """Initialize the playlist tree model.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.root_items: list[PlaylistItem] = []
        self.id_to_item: dict[Any, PlaylistItem] = {}

    def index(self, row: int, column: int, parent: QModelIndex | None = None) -> QModelIndex:
        """Create an index for the given row, column and parent.

        Args:
            row: Row number
            column: Column number
            parent: Parent index

        Returns:
            QModelIndex for the specified item
        """
        if not parent:
            parent = QModelIndex()
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            if row >= len(self.root_items):
                return QModelIndex()
            return self.createIndex(row, column, self.root_items[row])

        parent_item = parent.internalPointer()
        if row >= len(parent_item.children):
            return QModelIndex()

        return self.createIndex(row, column, parent_item.children[row])

    def parent(self, index: QModelIndex) -> QModelIndex:
        """Get the parent of the item at the given index.

        Args:
            index: Index of the item

        Returns:
            QModelIndex of the parent item
        """
        if not index.isValid():
            return QModelIndex()

        item = index.internalPointer()
        if not item or not item.parent_id:
            return QModelIndex()

        parent_item = self.id_to_item.get(item.parent_id)
        if not parent_item:
            return QModelIndex()

        # Find the parent's row
        if parent_item.parent_id is None:
            parent_row = self.root_items.index(parent_item)
            return self.createIndex(parent_row, 0, parent_item)
        else:
            parent_parent = self.id_to_item.get(parent_item.parent_id)
            if not parent_parent:
                return QModelIndex()
            parent_row = parent_parent.children.index(parent_item)
            return self.createIndex(parent_row, 0, parent_item)

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        """Get the number of rows under the given parent.

        Args:
            parent: Parent index

        Returns:
            Number of rows
        """
        if not parent:
            parent = QModelIndex()
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            return len(self.root_items)

        parent_item = parent.internalPointer()
        return len(parent_item.children)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        """Get the number of columns for the given parent.

        Args:
            parent: Parent index

        Returns:
            Number of columns (always 1 for this model)
        """
        return 1

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Get data for the given index and role.

        Args:
            index: Index of the item
            role: Data role

        Returns:
            Data for the index and role
        """
        if not index.isValid():
            return None

        item = index.internalPointer()

        if role == Qt.ItemDataRole.DisplayRole:
            if item.is_folder():
                return f"{item.name}"
            else:
                return f"{item.name} ({item.track_count})"
        elif role == Qt.ItemDataRole.DecorationRole:
            return item.get_icon()
        elif role == Qt.ItemDataRole.ToolTipRole:
            if hasattr(item, "description") and item.description:
                return item.description
            return item.name

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        """Get flags for the given index.

        Args:
            index: Index of the item

        Returns:
            Item flags
        """
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def clear(self) -> None:
        """Clear all items from the model."""
        self.beginResetModel()
        self.root_items.clear()
        self.id_to_item.clear()
        self.endResetModel()

    def add_item(self, item: PlaylistItem) -> None:
        """Add an item to the model.

        Args:
            item: Playlist item to add
        """
        self.beginResetModel()

        # Add to id lookup dictionary
        self.id_to_item[item.item_id] = item

        # Add to appropriate parent
        if item.parent_id is None:
            # Root item
            self.root_items.append(item)
        else:
            # Child item - find parent
            parent = self.id_to_item.get(item.parent_id)
            if parent:
                parent.add_child(item)

        self.endResetModel()

    def add_items(self, items: list[PlaylistItem]) -> None:
        """Add multiple items to the model.

        Args:
            items: List of playlist items to add
        """
        # First pass: add all items to id_to_item dict
        for item in items:
            self.id_to_item[item.item_id] = item

        # Second pass: build hierarchy
        self.beginResetModel()
        for item in items:
            if item.parent_id is None:
                # Root item
                self.root_items.append(item)
            else:
                # Child item - find parent
                parent = self.id_to_item.get(item.parent_id)
                if parent:
                    parent.add_child(item)

        self.endResetModel()
