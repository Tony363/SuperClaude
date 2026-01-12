"""
Comprehensive pytest unit tests for Calculator class.

Test Strategy:
- Unit tests following AAA pattern (Arrange-Act-Assert)
- Coverage of all four operations: add, subtract, multiply, divide
- Edge cases: zero, negative numbers, floats, large numbers
- Boundary testing: float precision, integer overflow scenarios
- Error handling: division by zero

Coverage Target: 100% for Calculator class
"""

import math

import pytest

from calculator import Calculator

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def calc():
    """Provide a Calculator instance for each test."""
    return Calculator()


# =============================================================================
# Test Class: Addition
# =============================================================================


class TestAdd:
    """Unit tests for Calculator.add() method."""

    # Happy Path Tests
    def test_add_positive_integers(self, calc):
        """Test adding two positive integers."""
        # Arrange
        a, b = 2, 3

        # Act
        result = calc.add(a, b)

        # Assert
        assert result == 5

    def test_add_negative_integers(self, calc):
        """Test adding two negative integers."""
        assert calc.add(-2, -3) == -5

    def test_add_mixed_signs(self, calc):
        """Test adding positive and negative integers."""
        assert calc.add(5, -3) == 2
        assert calc.add(-5, 3) == -2

    def test_add_floats(self, calc):
        """Test adding floating point numbers."""
        result = calc.add(1.5, 2.5)
        assert result == 4.0

    def test_add_mixed_int_float(self, calc):
        """Test adding integer and float."""
        assert calc.add(2, 3.5) == 5.5
        assert calc.add(3.5, 2) == 5.5

    # Edge Cases
    def test_add_zero(self, calc):
        """Test adding zero (identity property)."""
        assert calc.add(5, 0) == 5
        assert calc.add(0, 5) == 5
        assert calc.add(0, 0) == 0

    def test_add_large_numbers(self, calc):
        """Test adding very large numbers."""
        large = 10**15
        assert calc.add(large, large) == 2 * large

    def test_add_small_floats(self, calc):
        """Test adding very small floating point numbers."""
        result = calc.add(0.1, 0.2)
        assert math.isclose(result, 0.3, rel_tol=1e-9)

    def test_add_negative_zero(self, calc):
        """Test adding with negative zero."""
        assert calc.add(-0.0, 5) == 5
        assert calc.add(5, -0.0) == 5


# =============================================================================
# Test Class: Subtraction
# =============================================================================


class TestSubtract:
    """Unit tests for Calculator.subtract() method."""

    # Happy Path Tests
    def test_subtract_positive_integers(self, calc):
        """Test subtracting two positive integers."""
        assert calc.subtract(5, 3) == 2

    def test_subtract_negative_result(self, calc):
        """Test subtraction resulting in negative number."""
        assert calc.subtract(3, 5) == -2

    def test_subtract_negative_integers(self, calc):
        """Test subtracting negative integers."""
        assert calc.subtract(-5, -3) == -2
        assert calc.subtract(-3, -5) == 2

    def test_subtract_mixed_signs(self, calc):
        """Test subtracting with mixed signs."""
        assert calc.subtract(5, -3) == 8
        assert calc.subtract(-5, 3) == -8

    def test_subtract_floats(self, calc):
        """Test subtracting floating point numbers."""
        result = calc.subtract(5.5, 2.5)
        assert result == 3.0

    # Edge Cases
    def test_subtract_zero(self, calc):
        """Test subtracting zero (identity property)."""
        assert calc.subtract(5, 0) == 5
        assert calc.subtract(0, 5) == -5
        assert calc.subtract(0, 0) == 0

    def test_subtract_same_numbers(self, calc):
        """Test subtracting same numbers equals zero."""
        assert calc.subtract(5, 5) == 0
        assert calc.subtract(-5, -5) == 0
        assert calc.subtract(3.14, 3.14) == 0

    def test_subtract_large_numbers(self, calc):
        """Test subtracting very large numbers."""
        large = 10**15
        assert calc.subtract(large, large) == 0
        assert calc.subtract(large * 2, large) == large


# =============================================================================
# Test Class: Multiplication
# =============================================================================


class TestMultiply:
    """Unit tests for Calculator.multiply() method."""

    # Happy Path Tests
    def test_multiply_positive_integers(self, calc):
        """Test multiplying two positive integers."""
        assert calc.multiply(3, 4) == 12

    def test_multiply_negative_integers(self, calc):
        """Test multiplying two negative integers (positive result)."""
        assert calc.multiply(-3, -4) == 12

    def test_multiply_mixed_signs(self, calc):
        """Test multiplying positive and negative (negative result)."""
        assert calc.multiply(3, -4) == -12
        assert calc.multiply(-3, 4) == -12

    def test_multiply_floats(self, calc):
        """Test multiplying floating point numbers."""
        result = calc.multiply(2.5, 4.0)
        assert result == 10.0

    # Edge Cases
    def test_multiply_by_zero(self, calc):
        """Test multiplying by zero (zero property)."""
        assert calc.multiply(5, 0) == 0
        assert calc.multiply(0, 5) == 0
        assert calc.multiply(0, 0) == 0
        assert calc.multiply(-5, 0) == 0

    def test_multiply_by_one(self, calc):
        """Test multiplying by one (identity property)."""
        assert calc.multiply(5, 1) == 5
        assert calc.multiply(1, 5) == 5
        assert calc.multiply(-5, 1) == -5

    def test_multiply_by_negative_one(self, calc):
        """Test multiplying by negative one (sign flip)."""
        assert calc.multiply(5, -1) == -5
        assert calc.multiply(-5, -1) == 5

    def test_multiply_large_numbers(self, calc):
        """Test multiplying large numbers."""
        assert calc.multiply(10**6, 10**6) == 10**12

    def test_multiply_small_floats(self, calc):
        """Test multiplying very small numbers."""
        result = calc.multiply(0.001, 0.001)
        assert math.isclose(result, 0.000001, rel_tol=1e-9)

    def test_multiply_commutative(self, calc):
        """Test that multiplication is commutative."""
        assert calc.multiply(3, 7) == calc.multiply(7, 3)
        assert calc.multiply(2.5, 4) == calc.multiply(4, 2.5)


# =============================================================================
# Test Class: Division
# =============================================================================


class TestDivide:
    """Unit tests for Calculator.divide() method."""

    # Happy Path Tests
    def test_divide_positive_integers(self, calc):
        """Test dividing two positive integers."""
        assert calc.divide(10, 2) == 5.0

    def test_divide_with_remainder(self, calc):
        """Test division that results in a float."""
        assert calc.divide(7, 2) == 3.5

    def test_divide_negative_integers(self, calc):
        """Test dividing two negative integers (positive result)."""
        assert calc.divide(-10, -2) == 5.0

    def test_divide_mixed_signs(self, calc):
        """Test dividing with mixed signs (negative result)."""
        assert calc.divide(10, -2) == -5.0
        assert calc.divide(-10, 2) == -5.0

    def test_divide_floats(self, calc):
        """Test dividing floating point numbers."""
        assert calc.divide(7.5, 2.5) == 3.0

    # Edge Cases
    def test_divide_zero_dividend(self, calc):
        """Test dividing zero by a number."""
        assert calc.divide(0, 5) == 0.0
        assert calc.divide(0, -5) == 0.0

    def test_divide_by_one(self, calc):
        """Test dividing by one (identity property)."""
        assert calc.divide(5, 1) == 5.0
        assert calc.divide(-5, 1) == -5.0

    def test_divide_by_negative_one(self, calc):
        """Test dividing by negative one (sign flip)."""
        assert calc.divide(5, -1) == -5.0
        assert calc.divide(-5, -1) == 5.0

    def test_divide_same_numbers(self, calc):
        """Test dividing number by itself equals one."""
        assert calc.divide(5, 5) == 1.0
        assert calc.divide(-5, -5) == 1.0
        assert calc.divide(3.14, 3.14) == 1.0

    def test_divide_small_result(self, calc):
        """Test division resulting in small number."""
        result = calc.divide(1, 1000)
        assert result == 0.001

    def test_divide_large_numbers(self, calc):
        """Test dividing large numbers."""
        assert calc.divide(10**12, 10**6) == 10**6

    # Error Cases
    def test_divide_by_zero_raises_error(self, calc):
        """Test that dividing by zero raises ZeroDivisionError."""
        with pytest.raises(ZeroDivisionError) as exc_info:
            calc.divide(10, 0)
        assert "Cannot divide by zero" in str(exc_info.value)

    def test_divide_by_zero_with_zero_dividend(self, calc):
        """Test that 0/0 also raises ZeroDivisionError."""
        with pytest.raises(ZeroDivisionError):
            calc.divide(0, 0)

    def test_divide_by_zero_with_negative(self, calc):
        """Test that negative/0 raises ZeroDivisionError."""
        with pytest.raises(ZeroDivisionError):
            calc.divide(-5, 0)

    def test_divide_by_zero_with_float(self, calc):
        """Test that float/0 raises ZeroDivisionError."""
        with pytest.raises(ZeroDivisionError):
            calc.divide(3.14, 0)


# =============================================================================
# Parametrized Tests for Comprehensive Coverage
# =============================================================================


class TestParametrized:
    """Parametrized tests for batch testing multiple inputs."""

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            (1, 1, 2),
            (0, 0, 0),
            (-1, 1, 0),
            (100, 200, 300),
            (1.5, 2.5, 4.0),
            (-1.5, -2.5, -4.0),
            (10**10, 10**10, 2 * 10**10),
        ],
    )
    def test_add_parametrized(self, calc, a, b, expected):
        """Parametrized addition tests."""
        assert calc.add(a, b) == expected

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            (5, 3, 2),
            (3, 5, -2),
            (0, 0, 0),
            (-5, -3, -2),
            (100, 50, 50),
            (1.5, 0.5, 1.0),
        ],
    )
    def test_subtract_parametrized(self, calc, a, b, expected):
        """Parametrized subtraction tests."""
        assert calc.subtract(a, b) == expected

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            (2, 3, 6),
            (0, 100, 0),
            (-2, 3, -6),
            (-2, -3, 6),
            (1.5, 2, 3.0),
            (10, 10, 100),
        ],
    )
    def test_multiply_parametrized(self, calc, a, b, expected):
        """Parametrized multiplication tests."""
        assert calc.multiply(a, b) == expected

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            (10, 2, 5.0),
            (7, 2, 3.5),
            (0, 5, 0.0),
            (-10, 2, -5.0),
            (-10, -2, 5.0),
            (1, 3, 1 / 3),
        ],
    )
    def test_divide_parametrized(self, calc, a, b, expected):
        """Parametrized division tests."""
        assert math.isclose(calc.divide(a, b), expected, rel_tol=1e-9)


# =============================================================================
# Special Value Tests
# =============================================================================


class TestSpecialValues:
    """Tests for special floating point values."""

    def test_add_infinity(self, calc):
        """Test addition with infinity."""
        assert calc.add(float("inf"), 1) == float("inf")
        assert calc.add(float("-inf"), 1) == float("-inf")

    def test_multiply_infinity(self, calc):
        """Test multiplication with infinity."""
        assert calc.multiply(float("inf"), 2) == float("inf")
        assert calc.multiply(float("inf"), -1) == float("-inf")

    def test_divide_by_infinity(self, calc):
        """Test division by infinity."""
        assert calc.divide(1, float("inf")) == 0.0

    def test_operations_with_nan(self, calc):
        """Test that NaN propagates through operations."""
        nan = float("nan")
        assert math.isnan(calc.add(nan, 1))
        assert math.isnan(calc.subtract(nan, 1))
        assert math.isnan(calc.multiply(nan, 1))
        assert math.isnan(calc.divide(nan, 1))


# =============================================================================
# Property Tests (Mathematical Properties)
# =============================================================================


class TestMathematicalProperties:
    """Tests verifying mathematical properties hold."""

    def test_addition_commutative(self, calc):
        """Test a + b = b + a."""
        assert calc.add(3, 5) == calc.add(5, 3)
        assert calc.add(-2, 7) == calc.add(7, -2)

    def test_addition_associative(self, calc):
        """Test (a + b) + c = a + (b + c)."""
        a, b, c = 2, 3, 4
        assert calc.add(calc.add(a, b), c) == calc.add(a, calc.add(b, c))

    def test_multiplication_commutative(self, calc):
        """Test a * b = b * a."""
        assert calc.multiply(3, 5) == calc.multiply(5, 3)
        assert calc.multiply(-2, 7) == calc.multiply(7, -2)

    def test_multiplication_associative(self, calc):
        """Test (a * b) * c = a * (b * c)."""
        a, b, c = 2, 3, 4
        result1 = calc.multiply(calc.multiply(a, b), c)
        result2 = calc.multiply(a, calc.multiply(b, c))
        assert result1 == result2

    def test_distributive_property(self, calc):
        """Test a * (b + c) = a*b + a*c."""
        a, b, c = 2, 3, 4
        left = calc.multiply(a, calc.add(b, c))
        right = calc.add(calc.multiply(a, b), calc.multiply(a, c))
        assert left == right

    def test_subtraction_inverse_of_addition(self, calc):
        """Test (a + b) - b = a."""
        a, b = 5, 3
        assert calc.subtract(calc.add(a, b), b) == a

    def test_division_inverse_of_multiplication(self, calc):
        """Test (a * b) / b = a (for b != 0)."""
        a, b = 5, 3
        result = calc.divide(calc.multiply(a, b), b)
        assert math.isclose(result, a, rel_tol=1e-9)


# =============================================================================
# Type Return Tests
# =============================================================================


class TestReturnTypes:
    """Tests verifying correct return types."""

    def test_add_returns_int_for_int_inputs(self, calc):
        """Test that add returns int when given int inputs."""
        result = calc.add(2, 3)
        assert isinstance(result, int)

    def test_add_returns_float_for_float_inputs(self, calc):
        """Test that add returns float when given float inputs."""
        result = calc.add(2.0, 3.0)
        assert isinstance(result, float)

    def test_divide_always_returns_float(self, calc):
        """Test that divide always returns float."""
        result = calc.divide(10, 2)
        assert isinstance(result, float)
        assert result == 5.0
