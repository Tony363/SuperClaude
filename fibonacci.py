"""Fibonacci number computation with multiple implementation strategies.

This module provides efficient Fibonacci number calculation with proper
type hints, edge case handling, and multiple algorithmic approaches:

- fibonacci(): Iterative O(n) time, O(1) space - recommended for most uses
- fibonacci_recursive(): Memoized recursion O(n) time, O(n) space
- fibonacci_matrix(): Matrix exponentiation O(log n) time - for very large n
- fibonacci_generator(): Generator for sequences, memory efficient
"""

from functools import lru_cache
from typing import Iterator


def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number.

    Computes Fibonacci numbers using an iterative approach for optimal
    performance. The sequence starts with F(0) = 0, F(1) = 1.

    Args:
        n: The index of the Fibonacci number to calculate (0-indexed).
           Must be a non-negative integer.

    Returns:
        The nth Fibonacci number.

    Raises:
        ValueError: If n is negative.
        TypeError: If n is not an integer.

    Examples:
        >>> fibonacci(0)
        0
        >>> fibonacci(1)
        1
        >>> fibonacci(10)
        55
        >>> fibonacci(50)
        12586269025
    """
    if not isinstance(n, int):
        raise TypeError(f"n must be an integer, got {type(n).__name__}")
    if n < 0:
        raise ValueError(f"n must be non-negative, got {n}")

    if n == 0:
        return 0
    if n == 1:
        return 1

    prev, curr = 0, 1
    for _ in range(2, n + 1):
        prev, curr = curr, prev + curr

    return curr


@lru_cache(maxsize=128)
def fibonacci_recursive(n: int) -> int:
    """Calculate the nth Fibonacci number using memoized recursion.

    Uses functools.lru_cache for automatic memoization, making this
    approach efficient for repeated calls with overlapping subproblems.

    Args:
        n: The index of the Fibonacci number to calculate (0-indexed).
           Must be a non-negative integer.

    Returns:
        The nth Fibonacci number.

    Raises:
        ValueError: If n is negative.
        TypeError: If n is not an integer.

    Examples:
        >>> fibonacci_recursive(0)
        0
        >>> fibonacci_recursive(10)
        55
    """
    if not isinstance(n, int):
        raise TypeError(f"n must be an integer, got {type(n).__name__}")
    if n < 0:
        raise ValueError(f"n must be non-negative, got {n}")

    if n < 2:
        return n

    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)


def fibonacci_generator(limit: int) -> Iterator[int]:
    """Generate Fibonacci numbers up to the nth term.

    A generator function yielding Fibonacci numbers lazily, useful
    for iterating over a sequence without storing all values in memory.

    Args:
        limit: The number of Fibonacci terms to generate.
               Must be a non-negative integer.

    Yields:
        Fibonacci numbers from F(0) to F(limit-1).

    Raises:
        ValueError: If limit is negative.
        TypeError: If limit is not an integer.

    Examples:
        >>> list(fibonacci_generator(7))
        [0, 1, 1, 2, 3, 5, 8]
    """
    if not isinstance(limit, int):
        raise TypeError(f"limit must be an integer, got {type(limit).__name__}")
    if limit < 0:
        raise ValueError(f"limit must be non-negative, got {limit}")

    a, b = 0, 1
    for _ in range(limit):
        yield a
        a, b = b, a + b


def fibonacci_matrix(n: int) -> int:
    """Calculate the nth Fibonacci number using matrix exponentiation.

    Uses the matrix identity:
        [[F(n+1), F(n)], [F(n), F(n-1)]] = [[1,1], [1,0]]^n

    This provides O(log n) time complexity through binary exponentiation,
    making it the most efficient approach for very large values of n.

    Args:
        n: The index of the Fibonacci number to calculate (0-indexed).
           Must be a non-negative integer.

    Returns:
        The nth Fibonacci number.

    Raises:
        ValueError: If n is negative.
        TypeError: If n is not an integer.

    Examples:
        >>> fibonacci_matrix(0)
        0
        >>> fibonacci_matrix(10)
        55
        >>> fibonacci_matrix(100)
        354224848179261915075
    """
    if not isinstance(n, int):
        raise TypeError(f"n must be an integer, got {type(n).__name__}")
    if n < 0:
        raise ValueError(f"n must be non-negative, got {n}")

    if n == 0:
        return 0
    if n == 1:
        return 1

    def _matrix_multiply(
        a: tuple[tuple[int, int], tuple[int, int]],
        b: tuple[tuple[int, int], tuple[int, int]],
    ) -> tuple[tuple[int, int], tuple[int, int]]:
        """Multiply two 2x2 matrices represented as nested tuples."""
        return (
            (
                a[0][0] * b[0][0] + a[0][1] * b[1][0],
                a[0][0] * b[0][1] + a[0][1] * b[1][1],
            ),
            (
                a[1][0] * b[0][0] + a[1][1] * b[1][0],
                a[1][0] * b[0][1] + a[1][1] * b[1][1],
            ),
        )

    def _matrix_power(
        matrix: tuple[tuple[int, int], tuple[int, int]], power: int
    ) -> tuple[tuple[int, int], tuple[int, int]]:
        """Compute matrix^power using binary exponentiation for O(log n)."""
        if power == 1:
            return matrix

        if power % 2 == 0:
            half = _matrix_power(matrix, power // 2)
            return _matrix_multiply(half, half)

        return _matrix_multiply(matrix, _matrix_power(matrix, power - 1))

    base_matrix: tuple[tuple[int, int], tuple[int, int]] = ((1, 1), (1, 0))
    result = _matrix_power(base_matrix, n)

    return result[0][1]


if __name__ == "__main__":
    # Quick demonstration
    print("First 15 Fibonacci numbers:")
    print(list(fibonacci_generator(15)))

    print(f"\nF(50) = {fibonacci(50)}")
    print(f"F(100) via matrix = {fibonacci_matrix(100)}")
