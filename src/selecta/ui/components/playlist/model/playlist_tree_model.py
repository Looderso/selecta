from typing import Any

from PyQt6.QtCore import QAbstractItemModel, QModelIndex, Qt

from selecta.ui.components.playlist.base_items import BasePlaylistItem


class PlaylistTreeModel(QAbstractItemModel):
    """Model for displaying playlists in a tree view."""

    def __init__(self, parent=None):
        """Initialize the playlist tree model.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.root_items: list[BasePlaylistItem] = []
        self.id_to_item: dict[Any, BasePlaylistItem] = {}
        # This flag is kept for backward compatibility but no longer specific to Rekordbox
        # All platforms with folder support will use this model
        # Dictionary to track internal IDs for indexes to ensure proper uniqueness
        self._index_internal_ids = {}

    def createIndex(self, row: int, column: int, ptr: Any = None, internal_id: str = "") -> "QModelIndex":
        """Override createIndex to support internal IDs for uniquely identifying indexes.

        Args:
            row: Row number
            column: Column number
            ptr: Internal pointer
            internal_id: Optional internal ID string to ensure unique identification

        Returns:
            The created QModelIndex
        """
        # Create the index
        index = super().createIndex(row, column, ptr)

        # Store the internal ID for this index
        if internal_id:
            # Create a hash for this index that we can look up later for comparison
            # This is necessary because QModelIndex objects can't be extended
            # or subclassed directly in PyQt
            index_hash = hash((index.internalId(), index.row(), index.column()))
            self._index_internal_ids[index_hash] = internal_id

        return index

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
            # This is a root item
            if row >= len(self.root_items):
                return QModelIndex()

            # Get the root item
            root_item = self.root_items[row]

            # Create an internal ID based on path to distinguish items across different parents
            # This is crucial for fixing the selection issue - items in different folders
            # at the same row position must have different internal IDs
            item_path = f"root/{row}/{root_item.item_id}"

            # Create index with internal path-based ID
            return self.createIndex(row, column, root_item, internal_id=item_path)

        # This is a child item
        parent_item = parent.internalPointer()
        if row >= len(parent_item.children):
            return QModelIndex()

        # Get the child item
        child_item = parent_item.children[row]

        # Create path ID: parent_id/row/item_id to ensure uniqueness across parent folders
        # This ensures even if two different folders have items at the same row position,
        # they will have different path IDs
        parent_id = getattr(parent_item, "item_id", "unknown")
        item_path = f"{parent_id}/{row}/{child_item.item_id}"

        # Create index with internal path-based ID
        return self.createIndex(row, column, child_item, internal_id=item_path)

    # The parent method has multiple overloads in PyQt6 which causes type checking issues
    # One takes a QModelIndex and returns QModelIndex, the other takes no args and returns QObject
    # We're implementing the first version only
    def parent(self, child: QModelIndex) -> QModelIndex:  # type: ignore[override]
        """Get the parent of the item at the given index.

        Args:
            child: Index of the item

        Returns:
            QModelIndex of the parent item
        """
        if not child.isValid():
            return QModelIndex()

        item = child.internalPointer()
        if not item:
            return QModelIndex()

        if not item.parent_id:
            return QModelIndex()

        parent_item = self.id_to_item.get(item.parent_id)
        if not parent_item:
            return QModelIndex()

        parent_id = getattr(parent_item, "item_id", "Unknown")

        # Find the parent's row
        if parent_item.parent_id is None:
            # Root parent
            try:
                parent_row = self.root_items.index(parent_item)
                # Create path-based internal ID for parent
                parent_path_id = f"root/{parent_row}/{parent_id}"
                index = self.createIndex(parent_row, 0, parent_item, internal_id=parent_path_id)
                return index
            except ValueError:
                return QModelIndex()
        else:
            # Nested parent
            parent_parent = self.id_to_item.get(parent_item.parent_id)
            if not parent_parent:
                return QModelIndex()

            try:
                parent_row = parent_parent.children.index(parent_item)
                # Create path-based internal ID for parent
                grandparent_id = getattr(parent_parent, "item_id", "unknown")
                parent_path_id = f"{grandparent_id}/{parent_row}/{parent_id}"
                index = self.createIndex(parent_row, 0, parent_item, internal_id=parent_path_id)
                return index
            except ValueError:
                return QModelIndex()

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

        # Get the folder status
        is_folder = item.is_folder() if hasattr(item, "is_folder") else False

        if role == Qt.ItemDataRole.DisplayRole:
            if is_folder:
                return f"{item.name}"
            else:
                return f"{item.name} ({item.track_count})"
        elif role == Qt.ItemDataRole.DecorationRole:
            return item.get_icon()
        elif role == Qt.ItemDataRole.ToolTipRole:
            from selecta.core.utils.type_helpers import has_description

            # Create a tooltip with platform info if available
            tooltip = item.name
            from selecta.core.utils.type_helpers import has_synced_platforms

            if has_description(item):
                tooltip = item.description

            if has_synced_platforms(item) and item.get_platform_icons():
                platforms_str = ", ".join(p.capitalize() for p in item.get_platform_icons())
                tooltip += f"\n\nSynced with: {platforms_str}"

            return tooltip
        elif role == Qt.ItemDataRole.UserRole:
            # Return platform icons for custom drawing if available
            from selecta.core.utils.type_helpers import has_synced_platforms

            if has_synced_platforms(item):
                return item.get_platform_icons()

        # Include folder status in the font data
        elif role == Qt.ItemDataRole.FontRole:
            from PyQt6.QtGui import QFont

            font = QFont()
            if is_folder:
                font.setBold(True)
            return font

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

    def compare_indices(self, index1: QModelIndex, index2: QModelIndex) -> bool:
        """Compare two index objects using our internal IDs for uniqueness.

        This method is used to determine if two indices are truly the same,
        regardless of their row/column position. It helps prevent the selection
        of multiple items at the same position in different parent folders.

        Args:
            index1: First index to compare
            index2: Second index to compare

        Returns:
            True if the indices should be considered equal, False otherwise
        """
        # If either is invalid, they're only equal if both are invalid
        if not index1.isValid() or not index2.isValid():
            return not index1.isValid() and not index2.isValid()

        # Standard comparison first - these must match
        if index1.row() != index2.row() or index1.column() != index2.column():
            return False

        # Check if either has an internal ID
        hash1 = hash((index1.internalId(), index1.row(), index1.column()))
        hash2 = hash((index2.internalId(), index2.row(), index2.column()))

        id1 = self._index_internal_ids.get(hash1)
        id2 = self._index_internal_ids.get(hash2)

        # If both have internal IDs, use those for comparison
        if id1 and id2:
            result = id1 == id2
            return result

        # Otherwise fall back to standard pointer comparison
        item1 = index1.internalPointer()
        item2 = index2.internalPointer()

        # If both have internal pointers, compare directly
        if item1 and item2:
            result = item1 is item2
            return result

        # Last resort - use QModelIndex's built-in comparison
        result = index1 == index2
        return result

    def clear(self) -> None:
        """Clear all items from the model."""
        self.beginResetModel()
        self.root_items.clear()
        self.id_to_item.clear()
        # Clear internal tracking structures
        self._index_internal_ids.clear()
        self.endResetModel()

    def add_item(self, item: BasePlaylistItem) -> None:
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

    def add_items(self, items: list[BasePlaylistItem]) -> None:
        """Add multiple items to the model.

        Args:
            items: List of playlist items to add
        """
        # Check if these items need folder priority sorting
        needs_folder_priority = False
        if items and len(items) > 0 and hasattr(items[0], "is_folder"):
            needs_folder_priority = True

        # First pass: add all items to id_to_item dict, being careful about duplicates
        self.id_to_item.clear()  # Clear any existing items
        for item in items:
            # Skip duplicate IDs
            if item.item_id in self.id_to_item:
                continue
            self.id_to_item[item.item_id] = item

        # Clear existing root items before building new hierarchy
        self.root_items.clear()

        # Second pass: build hierarchy
        self.beginResetModel()
        root_count = 0
        child_count = 0
        orphan_count = 0

        # Sort items by folder status first for platforms with folder support
        if needs_folder_priority:
            # Process folders first, then regular playlists
            # This ensures folders are ready to receive their children
            folder_items = [item for item in items if item.is_folder()]
            non_folder_items = [item for item in items if not item.is_folder()]
            sorted_items = folder_items + non_folder_items
        else:
            sorted_items = items

        # Track which items have been added as children to avoid duplicates
        added_as_child = set()

        # Process all items in the sorted order
        for item in sorted_items:
            # Skip items not in id_to_item dict (duplicates were removed)
            if item.item_id not in self.id_to_item:
                continue

            # Skip items that would cause recursion (item can't be its own parent)
            if item.parent_id and item.parent_id == item.item_id:
                continue

            # If item has already been added as a child elsewhere, don't add it again
            if item.item_id in added_as_child:
                continue

            # Handle a few special cases for parent_id
            if item.parent_id is None or item.parent_id == "root" or item.parent_id == "":
                # Root item - treat empty string, "root", or None as indicators this is a root item
                self.root_items.append(item)
                root_count += 1
            else:
                # Child item - find parent
                parent = self.id_to_item.get(item.parent_id)
                if parent:
                    # Add to children
                    parent.add_child(item)
                    # Mark as added to children
                    added_as_child.add(item.item_id)
                    child_count += 1
                else:
                    # Found orphaned item with parent_id that doesn't exist
                    orphan_count += 1
                    # Add as root item anyway to make it visible
                    self.root_items.append(item)

        # Final check for child duplicates - detect recursion in the built tree
        def check_recursion(item, ancestors=None):
            if ancestors is None:
                ancestors = set()

            # Check for recursion
            if item.item_id in ancestors:
                return True

            # Add current item to ancestors
            new_ancestors = ancestors.copy()
            new_ancestors.add(item.item_id)

            # Check children
            if hasattr(item, "children"):
                for child in item.children:
                    if check_recursion(child, new_ancestors):
                        return True

            return False

        # Check each root item for recursion
        for root in self.root_items:
            check_recursion(root)

        self.endResetModel()
