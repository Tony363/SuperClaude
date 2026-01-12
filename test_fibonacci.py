"""Unit tests for Fibonacci implementations.

Uses pytest with parametrized tests covering normal cases, edge cases,
and error handling for all three Fibonacci implementations.
"""

import pytest

from fibonacci import (
    fibonacci,
    fibonacci_generator,
    fibonacci_matrix,
    fibonacci_recursive,
)


class TestFibonacci:
    """Tests for the iterative fibonacci function."""

    @pytest.mark.parametrize(
        "n,expected",
        [
            (0, 0),
            (1, 1),
            (2, 1),
            (3, 2),
            (4, 3),
            (5, 5),
            (6, 8),
            (7, 13),
            (10, 55),
            (20, 6765),
            (50, 12586269025),
        ],
    )
    def test_known_values(self, n: int, expected: int) -> None:
        """Test fibonacci returns correct values for known inputs."""
        assert fibonacci(n) == expected

    def test_negative_raises_value_error(self) -> None:
        """Test that negative input raises ValueError."""
        with pytest.raises(ValueError, match="must be non-negative"):
            fibonacci(-1)

    def test_non_integer_raises_type_error(self) -> None:
        """Test that non-integer input raises TypeError."""
        with pytest.raises(TypeError, match="must be an integer"):
            fibonacci(3.14)  # type: ignore[arg-type]

        with pytest.raises(TypeError, match="must be an integer"):
            fibonacci("5")  # type: ignore[arg-type]

    def test_large_number(self) -> None:
        """Test computation of large Fibonacci numbers."""
        # F(100) is a 21-digit number
        result = fibonacci(100)
        assert result == 354224848179261915075


class TestFibonacciRecursive:
    """Tests for the memoized recursive fibonacci function."""

    @pytest.mark.parametrize(
        "n,expected",
        [
            (0, 0),
            (1, 1),
            (2, 1),
            (5, 5),
            (10, 55),
            (30, 832040),
        ],
    )
    def test_known_values(self, n: int, expected: int) -> None:
        """Test recursive fibonacci returns correct values."""
        assert fibonacci_recursive(n) == expected

    def test_negative_raises_value_error(self) -> None:
        """Test that negative input raises ValueError."""
        with pytest.raises(ValueError, match="must be non-negative"):
            fibonacci_recursive(-5)

    def test_non_integer_raises_type_error(self) -> None:
        """Test that non-integer input raises TypeError."""
        with pytest.raises(TypeError, match="must be an integer"):
            fibonacci_recursive(2.5)  # type: ignore[arg-type]

    def test_consistency_with_iterative(self) -> None:
        """Verify recursive matches iterative implementation."""
        for i in range(40):
            assert fibonacci_recursive(i) == fibonacci(i)


class TestFibonacciGenerator:
    """Tests for the fibonacci generator function."""

    def test_empty_sequence(self) -> None:
        """Test generator with limit=0 yields nothing."""
        assert list(fibonacci_generator(0)) == []

    def test_single_element(self) -> None:
        """Test generator with limit=1 yields only F(0)."""
        assert list(fibonacci_generator(1)) == [0]

    def test_first_ten(self) -> None:
        """Test first 10 Fibonacci numbers."""
        expected = [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
        assert list(fibonacci_generator(10)) == expected

    def test_negative_raises_value_error(self) -> None:
        """Test that negative limit raises ValueError."""
        with pytest.raises(ValueError, match="must be non-negative"):
            list(fibonacci_generator(-1))

    def test_non_integer_raises_type_error(self) -> None:
        """Test that non-integer limit raises TypeError."""
        with pytest.raises(TypeError, match="must be an integer"):
            list(fibonacci_generator(5.0))  # type: ignore[arg-type]

    def test_is_generator(self) -> None:
        """Verify function returns a generator object."""
        gen = fibonacci_generator(5)
        assert hasattr(gen, "__iter__")
        assert hasattr(gen, "__next__")


class TestFibonacciMatrix:
    """Tests for the matrix exponentiation fibonacci function."""

    @pytest.mark.parametrize(
        "n,expected",
        [
            (0, 0),
            (1, 1),
            (2, 1),
            (5, 5),
            (10, 55),
            (20, 6765),
            (50, 12586269025),
            (100, 354224848179261915075),
        ],
    )
    def test_known_values(self, n: int, expected: int) -> None:
        """Test matrix fibonacci returns correct values."""
        assert fibonacci_matrix(n) == expected

    def test_negative_raises_value_error(self) -> None:
        """Test that negative input raises ValueError."""
        with pytest.raises(ValueError, match="must be non-negative"):
            fibonacci_matrix(-1)

    def test_non_integer_raises_type_error(self) -> None:
        """Test that non-integer input raises TypeError."""
        with pytest.raises(TypeError, match="must be an integer"):
            fibonacci_matrix(3.14)  # type: ignore[arg-type]

    def test_very_large_number(self) -> None:
        """Test computation of very large Fibonacci numbers (O(log n) benefit)."""
        # F(500) - demonstrates O(log n) efficiency
        result = fibonacci_matrix(500)
        assert result > 10**100  # 500th Fibonacci has 105 digits
        # Verify it ends correctly (last few digits are stable)
        assert str(result).endswith("875")


class TestCrossImplementation:
    """Cross-validation between all implementations."""

    @pytest.mark.parametrize("n", range(35))
    def test_all_implementations_match(self, n: int) -> None:
        """Verify all implementations produce identical results."""
        iterative = fibonacci(n)
        recursive = fibonacci_recursive(n)
        matrix = fibonacci_matrix(n)
        generated = list(fibonacci_generator(n + 1))[-1] if n >= 0 else None

        assert iterative == recursive
        assert iterative == matrix
        if generated is not None:
            assert iterative == generated

    @pytest.mark.parametrize("n", [50, 75, 100])
    def test_large_values_match(self, n: int) -> None:
        """Verify iterative and matrix match for large values."""
        assert fibonacci(n) == fibonacci_matrix(n)
