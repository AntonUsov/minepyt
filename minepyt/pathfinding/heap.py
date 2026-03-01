"""
Binary Heap implementation for A* pathfinding

Based on mineflayer-pathfinder/lib/heap.js

This is an optimized min-heap where the element with the lowest 'f' value
is always at the top, allowing O(log n) insertion and removal.
"""

from __future__ import annotations

from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")


class BinaryHeap(Generic[T]):
    """
    A binary min-heap implementation optimized for pathfinding.

    Elements must have an 'f' attribute representing their priority.
    Lower 'f' values are at the top of the heap.
    """

    def __init__(self):
        # Start with a dummy element at index 0 for simpler math
        self._heap: List[Optional[T]] = [None]

    def size(self) -> int:
        """Get the number of elements in the heap"""
        return len(self._heap) - 1

    def is_empty(self) -> bool:
        """Check if the heap is empty"""
        return len(self._heap) == 1

    def push(self, value: T) -> None:
        """
        Add a value to the heap.

        Time complexity: O(log n)
        """
        # Add to the end
        self._heap.append(value)

        # Bubble up to correct position
        current = len(self._heap) - 1
        parent = current >> 1  # Integer division by 2

        while current > 1 and self._heap[parent].f > self._heap[current].f:
            # Swap with parent
            self._heap[parent], self._heap[current] = self._heap[current], self._heap[parent]
            current = parent
            parent = current >> 1

    def pop(self) -> Optional[T]:
        """
        Remove and return the minimum element.

        Time complexity: O(log n)
        """
        if self.is_empty():
            return None

        # Get the minimum (at index 1)
        minimum = self._heap[1]

        # Move last element to root
        self._heap[1] = self._heap[-1]
        self._heap.pop()

        size = len(self._heap) - 1
        if size < 2:
            return minimum

        # Bubble down
        value = self._heap[1]
        index = 1
        smaller_child = 2

        while smaller_child <= size:
            child_node = self._heap[smaller_child]

            # Check if right child is smaller
            if smaller_child < size - 1:
                right_child = self._heap[smaller_child + 1]
                if child_node.f > right_child.f:
                    smaller_child += 1
                    child_node = right_child

            # If value is smaller or equal to smallest child, we're done
            if value.f <= child_node.f:
                break

            # Swap with smaller child
            self._heap[index] = child_node
            self._heap[smaller_child] = value
            index = smaller_child
            smaller_child = index << 1  # Multiply by 2

        return minimum

    def update(self, value: T) -> None:
        """
        Update a value's position after its priority has changed.
        Assumes the value's 'f' has decreased.

        Time complexity: O(log n)
        """
        try:
            current = self._heap.index(value)
        except ValueError:
            return  # Value not in heap

        # Bubble up (since f should have decreased)
        parent = current >> 1

        while current > 1 and self._heap[parent].f > self._heap[current].f:
            self._heap[parent], self._heap[current] = self._heap[current], self._heap[parent]
            current = parent
            parent = current >> 1

    def peek(self) -> Optional[T]:
        """Get the minimum element without removing it"""
        if self.is_empty():
            return None
        return self._heap[1]

    def clear(self) -> None:
        """Remove all elements"""
        self._heap = [None]

    def __len__(self) -> int:
        return self.size()

    def __bool__(self) -> bool:
        return not self.is_empty()

    def __repr__(self) -> str:
        items = self._heap[1:]
        return f"BinaryHeap({items})"
