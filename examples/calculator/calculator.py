"""Calculator module with basic arithmetic operations."""

from typing import Union

Number = Union[int, float]


class Calculator:
    """A simple calculator class with basic arithmetic operations."""

    def add(self, a: Number, b: Number) -> Number:
        """Add two numbers.

        Args:
            a: First number
            b: Second number

        Returns:
            Sum of a and b
        """
        return a + b

    def subtract(self, a: Number, b: Number) -> Number:
        """Subtract b from a.

        Args:
            a: First number (minuend)
            b: Second number (subtrahend)

        Returns:
            Difference of a and b
        """
        return a - b

    def multiply(self, a: Number, b: Number) -> Number:
        """Multiply two numbers.

        Args:
            a: First number
            b: Second number

        Returns:
            Product of a and b
        """
        return a * b

    def divide(self, a: Number, b: Number) -> float:
        """Divide a by b.

        Args:
            a: Dividend
            b: Divisor

        Returns:
            Quotient of a divided by b

        Raises:
            ZeroDivisionError: If b is zero
        """
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return a / b
