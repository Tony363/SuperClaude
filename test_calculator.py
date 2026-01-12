"""Comprehensive pytest unit tests for Calculator class.

Test Strategy:
- Happy path tests for all operations
- Edge cases: zero, negative numbers, floating-point precision
- Boundary tests: large numbers, small decimals
- Error handling: division by zero
- Type handling: integers, floats, mixed types

Coverage Target: 100% of Calculator methods
"""

import math
import pytest
from calculator import Calculator


class TestCalculatorSetup:
    """Test fixture and setup verification."""

    @pytest.fixture
    def calc(self):
        """Provide a Calculator instance for each test."""
        return Calculator()

    def test_calculator_instantiation(self, calc):
        """Verify Calculator can be instantiated."""
        assert calc is not None
        assert isinstance(calc, Calculator)


class TestAddition:
    """Unit tests for Calculator.add() method."""

    @pytest.fixture
    def calc(self):
        return Calculator()

    # Happy Path Tests
    def test_add_positive_integers(self, calc):
        """Add two positive integers."""
        assert calc.add(2, 3) == 5

    def test_add_negative_integers(self, calc):
        """Add two negative integers."""
        assert calc.add(-2, -3) == -5

    def test_add_mixed_signs(self, calc):
        """Add positive and negative integers."""
        assert calc.add(5, -3) == 2
        assert calc.add(-5, 3) == -2

    def test_add_floats(self, calc):
        """Add floating-point numbers."""
        result = calc.add(2.5, 3.7)
        assert math.isclose(result, 6.2, rel_tol=1e-9)

    # Edge Cases
    def test_add_zero(self, calc):
        """Adding zero should return the other operand."""
        assert calc.add(5, 0) == 5
        assert calc.add(0, 5) == 5
        assert calc.add(0, 0) == 0

    def test_add_negative_zero(self, calc):
        """Adding negative zero."""
        assert calc.add(5, -0.0) == 5.0
        assert calc.add(-0.0, 5) == 5.0

    # Boundary Tests
    def test_add_large_numbers(self, calc):
        """Add very large numbers."""
        large = 10**15
        assert calc.add(large, large) == 2 * large

    def test_add_small_decimals(self, calc):
        """Add very small decimal numbers."""
        result = calc.add(0.0000001, 0.0000002)
        assert math.isclose(result, 0.0000003, rel_tol=1e-9)

    def test_add_mixed_int_float(self, calc):
        """Add integer and float."""
        result = calc.add(5, 2.5)
        assert result == 7.5
        assert isinstance(result, float)

    # Floating-Point Precision
    def test_add_floating_point_precision(self, calc):
        """Test floating-point precision issues."""
        # 0.1 + 0.2 is famously not exactly 0.3 in floating-point
        result = calc.add(0.1, 0.2)
        assert math.isclose(result, 0.3, rel_tol=1e-9)

    # Commutative Property
    def test_add_commutative(self, calc):
        """Addition should be commutative: a + b == b + a."""
        assert calc.add(3, 7) == calc.add(7, 3)
        assert calc.add(-5, 10) == calc.add(10, -5)

    # Identity Property
    def test_add_identity(self, calc):
        """Zero is the identity element for addition."""
        for value in [1, -1, 100, -100, 0.5, -0.5]:
            assert calc.add(value, 0) == value
            assert calc.add(0, value) == value


class TestSubtraction:
    """Unit tests for Calculator.subtract() method."""

    @pytest.fixture
    def calc(self):
        return Calculator()

    # Happy Path Tests
    def test_subtract_positive_integers(self, calc):
        """Subtract two positive integers."""
        assert calc.subtract(5, 3) == 2

    def test_subtract_negative_integers(self, calc):
        """Subtract two negative integers."""
        assert calc.subtract(-5, -3) == -2

    def test_subtract_mixed_signs(self, calc):
        """Subtract with mixed signs."""
        assert calc.subtract(5, -3) == 8
        assert calc.subtract(-5, 3) == -8

    def test_subtract_floats(self, calc):
        """Subtract floating-point numbers."""
        result = calc.subtract(5.5, 2.3)
        assert math.isclose(result, 3.2, rel_tol=1e-9)

    # Edge Cases
    def test_subtract_zero(self, calc):
        """Subtracting zero should return the same value."""
        assert calc.subtract(5, 0) == 5
        assert calc.subtract(-5, 0) == -5

    def test_subtract_from_zero(self, calc):
        """Subtracting from zero gives negation."""
        assert calc.subtract(0, 5) == -5
        assert calc.subtract(0, -5) == 5

    def test_subtract_same_number(self, calc):
        """Subtracting a number from itself equals zero."""
        assert calc.subtract(5, 5) == 0
        assert calc.subtract(-5, -5) == 0
        assert calc.subtract(0, 0) == 0

    # Boundary Tests
    def test_subtract_large_numbers(self, calc):
        """Subtract very large numbers."""
        large = 10**15
        assert calc.subtract(large, large) == 0
        assert calc.subtract(large * 2, large) == large

    def test_subtract_small_decimals(self, calc):
        """Subtract very small decimal numbers."""
        result = calc.subtract(0.0000003, 0.0000001)
        assert math.isclose(result, 0.0000002, rel_tol=1e-9)

    # Non-Commutative Property
    def test_subtract_non_commutative(self, calc):
        """Subtraction is NOT commutative: a - b != b - a (usually)."""
        assert calc.subtract(5, 3) != calc.subtract(3, 5)
        assert calc.subtract(5, 3) == -calc.subtract(3, 5)

    def test_subtract_result_negative(self, calc):
        """Subtraction can produce negative results."""
        assert calc.subtract(3, 5) == -2


class TestMultiplication:
    """Unit tests for Calculator.multiply() method."""

    @pytest.fixture
    def calc(self):
        return Calculator()

    # Happy Path Tests
    def test_multiply_positive_integers(self, calc):
        """Multiply two positive integers."""
        assert calc.multiply(3, 4) == 12

    def test_multiply_negative_integers(self, calc):
        """Multiply two negative integers (result is positive)."""
        assert calc.multiply(-3, -4) == 12

    def test_multiply_mixed_signs(self, calc):
        """Multiply positive and negative (result is negative)."""
        assert calc.multiply(3, -4) == -12
        assert calc.multiply(-3, 4) == -12

    def test_multiply_floats(self, calc):
        """Multiply floating-point numbers."""
        result = calc.multiply(2.5, 4.0)
        assert math.isclose(result, 10.0, rel_tol=1e-9)

    # Edge Cases
    def test_multiply_by_zero(self, calc):
        """Multiplying by zero always gives zero."""
        assert calc.multiply(5, 0) == 0
        assert calc.multiply(0, 5) == 0
        assert calc.multiply(0, 0) == 0
        assert calc.multiply(-5, 0) == 0

    def test_multiply_by_one(self, calc):
        """One is the identity element for multiplication."""
        assert calc.multiply(5, 1) == 5
        assert calc.multiply(1, 5) == 5
        assert calc.multiply(-5, 1) == -5
        assert calc.multiply(1, -5) == -5

    def test_multiply_by_negative_one(self, calc):
        """Multiplying by -1 negates the number."""
        assert calc.multiply(5, -1) == -5
        assert calc.multiply(-5, -1) == 5

    # Boundary Tests
    def test_multiply_large_numbers(self, calc):
        """Multiply large numbers."""
        assert calc.multiply(10**7, 10**7) == 10**14

    def test_multiply_small_decimals(self, calc):
        """Multiply very small decimal numbers."""
        result = calc.multiply(0.001, 0.001)
        assert math.isclose(result, 0.000001, rel_tol=1e-9)

    def test_multiply_large_by_small(self, calc):
        """Multiply large number by small decimal."""
        result = calc.multiply(1000000, 0.000001)
        assert math.isclose(result, 1.0, rel_tol=1e-9)

    # Commutative Property
    def test_multiply_commutative(self, calc):
        """Multiplication should be commutative: a * b == b * a."""
        assert calc.multiply(3, 7) == calc.multiply(7, 3)
        assert calc.multiply(-5, 10) == calc.multiply(10, -5)

    # Associative Property
    def test_multiply_associative(self, calc):
        """Multiplication is associative: (a*b)*c == a*(b*c)."""
        a, b, c = 2, 3, 4
        left = calc.multiply(calc.multiply(a, b), c)
        right = calc.multiply(a, calc.multiply(b, c))
        assert left == right


class TestDivision:
    """Unit tests for Calculator.divide() method."""

    @pytest.fixture
    def calc(self):
        return Calculator()

    # Happy Path Tests
    def test_divide_positive_integers(self, calc):
        """Divide two positive integers."""
        assert calc.divide(10, 2) == 5.0

    def test_divide_negative_integers(self, calc):
        """Divide two negative integers (result is positive)."""
        assert calc.divide(-10, -2) == 5.0

    def test_divide_mixed_signs(self, calc):
        """Divide positive by negative (result is negative)."""
        assert calc.divide(10, -2) == -5.0
        assert calc.divide(-10, 2) == -5.0

    def test_divide_floats(self, calc):
        """Divide floating-point numbers."""
        result = calc.divide(7.5, 2.5)
        assert math.isclose(result, 3.0, rel_tol=1e-9)

    def test_divide_non_exact_result(self, calc):
        """Division producing non-integer result."""
        result = calc.divide(10, 3)
        assert math.isclose(result, 3.333333333333333, rel_tol=1e-9)

    # Edge Cases - Zero Handling
    def test_divide_by_zero_raises_exception(self, calc):
        """Division by zero should raise ZeroDivisionError."""
        with pytest.raises(ZeroDivisionError) as exc_info:
            calc.divide(10, 0)
        assert "Cannot divide by zero" in str(exc_info.value)

    def test_divide_by_zero_negative_numerator(self, calc):
        """Division by zero with negative numerator."""
        with pytest.raises(ZeroDivisionError):
            calc.divide(-10, 0)

    def test_divide_by_zero_float(self, calc):
        """Division by zero (as float)."""
        with pytest.raises(ZeroDivisionError):
            calc.divide(10.5, 0.0)

    def test_divide_zero_by_number(self, calc):
        """Zero divided by any non-zero number is zero."""
        assert calc.divide(0, 5) == 0.0
        assert calc.divide(0, -5) == 0.0
        assert calc.divide(0, 0.001) == 0.0

    # Boundary Tests
    def test_divide_by_one(self, calc):
        """Dividing by one returns the original number."""
        assert calc.divide(5, 1) == 5.0
        assert calc.divide(-5, 1) == -5.0
        assert calc.divide(0, 1) == 0.0

    def test_divide_by_negative_one(self, calc):
        """Dividing by -1 negates the number."""
        assert calc.divide(5, -1) == -5.0
        assert calc.divide(-5, -1) == 5.0

    def test_divide_number_by_itself(self, calc):
        """Any non-zero number divided by itself equals one."""
        assert calc.divide(5, 5) == 1.0
        assert calc.divide(-5, -5) == 1.0
        assert calc.divide(0.5, 0.5) == 1.0

    def test_divide_large_numbers(self, calc):
        """Divide large numbers."""
        assert calc.divide(10**15, 10**10) == 10**5

    def test_divide_small_decimals(self, calc):
        """Divide very small decimal numbers."""
        result = calc.divide(0.000001, 0.001)
        assert math.isclose(result, 0.001, rel_tol=1e-9)

    def test_divide_by_very_small_number(self, calc):
        """Dividing by a very small number produces large result."""
        result = calc.divide(1, 0.0001)
        assert math.isclose(result, 10000.0, rel_tol=1e-9)

    # Non-Commutative Property
    def test_divide_non_commutative(self, calc):
        """Division is NOT commutative: a / b != b / a (usually)."""
        assert calc.divide(10, 2) != calc.divide(2, 10)
        assert calc.divide(10, 2) == 5.0
        assert calc.divide(2, 10) == 0.2


class TestCalculatorIntegration:
    """Integration tests combining multiple operations."""

    @pytest.fixture
    def calc(self):
        return Calculator()

    def test_complex_expression(self, calc):
        """Test complex expression: (a + b) * c / d."""
        # (10 + 5) * 2 / 3 = 15 * 2 / 3 = 30 / 3 = 10
        step1 = calc.add(10, 5)
        step2 = calc.multiply(step1, 2)
        result = calc.divide(step2, 3)
        assert math.isclose(result, 10.0, rel_tol=1e-9)

    def test_chained_operations(self, calc):
        """Test chained operations."""
        # 100 - 50 + 25 - 10 = 65
        result = calc.add(
            calc.subtract(
                calc.add(calc.subtract(100, 50), 25),
                10
            ),
            0
        )
        assert result == 65

    def test_inverse_operations(self, calc):
        """Test that inverse operations cancel out."""
        original = 42
        # add then subtract
        assert calc.subtract(calc.add(original, 10), 10) == original
        # multiply then divide
        assert math.isclose(
            calc.divide(calc.multiply(original, 5), 5),
            original,
            rel_tol=1e-9
        )


class TestParameterizedOperations:
    """Parametrized tests for comprehensive coverage."""

    @pytest.fixture
    def calc(self):
        return Calculator()

    @pytest.mark.parametrize("a,b,expected", [
        (1, 1, 2),
        (0, 0, 0),
        (-1, -1, -2),
        (1.5, 2.5, 4.0),
        (100, -100, 0),
        (10**10, 10**10, 2 * 10**10),
    ])
    def test_add_parametrized(self, calc, a, b, expected):
        """Parametrized addition tests."""
        result = calc.add(a, b)
        assert math.isclose(result, expected, rel_tol=1e-9)

    @pytest.mark.parametrize("a,b,expected", [
        (5, 3, 2),
        (0, 0, 0),
        (-5, -3, -2),
        (3, 5, -2),
        (1.5, 0.5, 1.0),
    ])
    def test_subtract_parametrized(self, calc, a, b, expected):
        """Parametrized subtraction tests."""
        result = calc.subtract(a, b)
        assert math.isclose(result, expected, rel_tol=1e-9)

    @pytest.mark.parametrize("a,b,expected", [
        (2, 3, 6),
        (0, 100, 0),
        (-2, 3, -6),
        (-2, -3, 6),
        (1.5, 2, 3.0),
    ])
    def test_multiply_parametrized(self, calc, a, b, expected):
        """Parametrized multiplication tests."""
        result = calc.multiply(a, b)
        assert math.isclose(result, expected, rel_tol=1e-9)

    @pytest.mark.parametrize("a,b,expected", [
        (6, 3, 2.0),
        (0, 5, 0.0),
        (-6, 3, -2.0),
        (-6, -3, 2.0),
        (7, 2, 3.5),
    ])
    def test_divide_parametrized(self, calc, a, b, expected):
        """Parametrized division tests."""
        result = calc.divide(a, b)
        assert math.isclose(result, expected, rel_tol=1e-9)


class TestSpecialFloatValues:
    """Tests for special floating-point values."""

    @pytest.fixture
    def calc(self):
        return Calculator()

    def test_infinity_addition(self, calc):
        """Adding infinity."""
        inf = float('inf')
        assert calc.add(inf, 1) == inf
        assert calc.add(inf, inf) == inf

    def test_infinity_multiplication(self, calc):
        """Multiplying with infinity."""
        inf = float('inf')
        assert calc.multiply(inf, 2) == inf
        assert calc.multiply(inf, -1) == -inf

    def test_infinity_division(self, calc):
        """Dividing with infinity."""
        inf = float('inf')
        assert calc.divide(inf, 2) == inf
        assert calc.divide(1, inf) == 0.0

    def test_negative_infinity(self, calc):
        """Operations with negative infinity."""
        neg_inf = float('-inf')
        assert calc.add(neg_inf, 1) == neg_inf
        assert calc.multiply(neg_inf, -1) == float('inf')


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
