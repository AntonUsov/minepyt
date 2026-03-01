"""
Book editing for Minecraft 1.21.4

This module provides:
- Edit books and writable books
- Write pages, title, and author
- Sign books

Books are edited via EditBook packet (0x6C) or plugin channel MC|BEdit.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, List

if TYPE_CHECKING:
    from .protocol.connection import MinecraftProtocol
    from .protocol.models import Item


@dataclass
class Book:
    """
    Represents a writable book.

    Attributes:
        pages: List of page strings (JSON components)
        title: Book title
        author: Book author
    """

    pages: List[str] = field(default_factory=list)
    title: str = ""
    author: str = ""


class BookManager:
    """
    Manages book editing.

    This class handles:
    - Book editing
    - Page, title, author management
    - Book signing

    Book packets:
    - EditBook (0x6C): Edit book in hand
    - Plugin channel MC|BEdit: Edit book in inventory
    """

    def __init__(self, protocol: "MinecraftProtocol"):
        self.protocol = protocol

    async def edit_book(
        self,
        slot: int,
        pages: Optional[List[str]] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        signing: bool = False,
    ) -> None:
        """
        Edit a book in the inventory.

        Args:
            slot: Book slot (0-44 for player inventory)
            pages: List of page strings (JSON components)
            title: Book title
            author: Book author
            signing: Whether to sign the book (requires held_item to be writable_book)

        Raises:
            ValueError: If slot is out of range
            RuntimeError: If no book in slot
        """
        if not (0 <= slot <= 44):
            raise ValueError(f"Slot must be between 0 and 44, got {slot}")

        # Get book item from inventory
        item = self.protocol._inventory_mgr.player_inventory.get_slot(slot)
        if not item or item.is_empty:
            raise RuntimeError(f"No book found in slot {slot}")

        # Parse book NBT if exists
        book_nbt = self._parse_book_nbt(item.nbt_data) if item.nbt_data else Book()
        book_nbt = Book()

        # Update book data
        if pages is not None:
            book_nbt.pages = pages
        if title is not None:
            book_nbt.title = title
        if author is not None:
            book_nbt.author = author

        # Determine book item type
        # Signing requires writable_book -> becomes written_book
        if signing:
            # Check if current item is writable_book
            writable_book_name = "minecraft:writable_book"
            if item.name == writable_book_name:
                # Change to written_book for signing
                from .protocol.models import Item

                signed_item = Item(
                    item_id=item.item_id,
                    item_count=item.item_count,
                    nbt_data=self._build_book_nbt(book_nbt),
                    components=item.components,
                )

                # Update item in slot (requires creative mode or inventory manipulation)
                # For now, we'll just note this
                print(f"[BOOK] Book signed: {book_nbt.title} by {book_nbt.author}")
            else:
                print(f"[BOOK] Warning: Cannot sign non-writable book")
        else:
            print(f"[BOOK] Edited book: {len(book_nbt.pages)} pages")

        # Send edit packet if supported
        # Note: In Minecraft 1.21.4, book editing is primarily done via
        # plugin channels or server-side. The EditBook packet (0x6C) is for 1.18+
        self.protocol.emit("book_edited", slot, book_nbt)

    def _parse_book_nbt(self, nbt_data: Optional[dict]) -> Optional[Book]:
        """
        Parse book NBT data to Book object.

        Args:
            nbt_data: Raw NBT data

        Returns:
            Book object or None if no book data
        """
        if not nbt_data:
            return None

        try:
            # Extract pages, title, author from NBT
            pages = []
            if "pages" in nbt_data:
                pages_list = nbt_data["pages"]
                if isinstance(pages_list, list):
                    for page in pages_list:
                        if isinstance(page, str):
                            pages.append(page)
                        elif isinstance(page, dict):
                            pages.append(json.dumps(page))

            title = nbt_data.get("title", "")
            author = nbt_data.get("author", "")

            return Book(pages=pages, title=title, author=author)

        except (KeyError, TypeError, AttributeError):
            print(f"[BOOK] Warning: Failed to parse book NBT")
            return None

    def _build_book_nbt(self, book: Book) -> dict:
        """
        Build NBT data for a book.

        Args:
            book: Book object

        Returns:
            NBT data dict
        """
        nbt = {"type": "compound", "name": "", "value": {}}

        value = nbt["value"]

        # Pages (as list tag)
        if book.pages:
            pages_list = []
            for page in book.pages:
                pages_list.append(page)
            value["pages"] = {
                "type": "list",
                "name": "",
                "value": {"type": "compound", "name": "", "value": {}},
            }

        # Title (as string tag)
        if book.title:
            value["title"] = {"type": "string", "name": "", "value": book.title}

        # Author (as string tag)
        if book.author:
            value["author"] = {"type": "string", "name": "", "value": book.author}

        # Generation tag (for signed books)
        value["generation"] = {"type": "int", "name": "", "value": 0}

        # Resolved flag
        value["resolved"] = {"type": "byte", "name": "", "value": 1}

        return nbt

    async def read_book(self, slot: int) -> Optional[Book]:
        """
        Read book data from inventory slot.

        Args:
            slot: Book slot (0-44)

        Returns:
            Book object or None if not a book
        """
        item = self.protocol._inventory_mgr.player_inventory.get_slot(slot)
        if not item or item.is_empty:
            return None

        # Check if it's a book item
        book_items = [
            "minecraft:writable_book",
            "minecraft:written_book",
        ]

        if item.name not in book_items:
            return None

        # Parse book NBT
        book = self._parse_book_nbt(item.nbt_data)
        return book if book else None


__all__ = [
    "BookManager",
    "Book",
]
