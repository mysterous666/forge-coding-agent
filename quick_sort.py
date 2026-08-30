"""快速排序算法。"""

from collections.abc import MutableSequence
from typing import TypeVar

T = TypeVar("T")


def quick_sort(items: MutableSequence[T]) -> MutableSequence[T]:
    """使用快速排序原地升序排列序列，并返回该序列。"""

    def partition(left: int, right: int) -> int:
        pivot = items[right]
        boundary = left
        for index in range(left, right):
            if items[index] <= pivot:
                items[boundary], items[index] = items[index], items[boundary]
                boundary += 1
        items[boundary], items[right] = items[right], items[boundary]
        return boundary

    def sort(left: int, right: int) -> None:
        if left >= right:
            return
        pivot_index = partition(left, right)
        sort(left, pivot_index - 1)
        sort(pivot_index + 1, right)

    sort(0, len(items) - 1)
    return items


if __name__ == "__main__":
    numbers = [8, 3, 1, 7, 0, 10, 2]
    quick_sort(numbers)
    print(numbers)
