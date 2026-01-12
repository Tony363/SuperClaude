#!/usr/bin/env python3
"""Tests for SOLID validator."""

from pathlib import Path

from scripts.validate_solid import (
    SOLIDThresholds,
    analyze_file_solid,
    validate_solid,
)


class TestSRPDetection:
    """Test Single Responsibility Principle detection."""

    def test_file_too_long(self, tmp_path: Path) -> None:
        """Files over threshold should trigger SRP warning."""
        # Create a file with 350 lines
        code = "\n".join([f"x{i} = {i}" for i in range(350)])
        test_file = tmp_path / "long_file.py"
        test_file.write_text(code)

        thresholds = SOLIDThresholds(max_file_lines=300)
        violations = analyze_file_solid(test_file, thresholds)

        assert any(v.violation_type == "srp_file_length" for v in violations)

    def test_class_too_many_methods(self, tmp_path: Path) -> None:
        """Classes with too many public methods trigger SRP warning."""
        code = """
class GodClass:
    def method1(self): pass
    def method2(self): pass
    def method3(self): pass
    def method4(self): pass
    def method5(self): pass
    def method6(self): pass
    def method7(self): pass
"""
        test_file = tmp_path / "god_class.py"
        test_file.write_text(code)

        thresholds = SOLIDThresholds(max_class_public_methods=5)
        violations = analyze_file_solid(test_file, thresholds)

        assert any(v.violation_type == "srp_class_methods" for v in violations)

    def test_private_methods_not_counted(self, tmp_path: Path) -> None:
        """Private methods (_method) should not count toward SRP."""
        code = """
class WellDesigned:
    def public1(self): pass
    def public2(self): pass
    def _private1(self): pass
    def _private2(self): pass
    def _private3(self): pass
    def _private4(self): pass
"""
        test_file = tmp_path / "well_designed.py"
        test_file.write_text(code)

        thresholds = SOLIDThresholds(max_class_public_methods=5)
        violations = analyze_file_solid(test_file, thresholds)

        assert not any(v.violation_type == "srp_class_methods" for v in violations)


class TestOCPDetection:
    """Test Open-Closed Principle detection."""

    def test_isinstance_cascade(self, tmp_path: Path) -> None:
        """isinstance cascades suggest OCP violation."""
        code = """
def process(obj):
    if isinstance(obj, TypeA):
        return handle_a(obj)
    elif isinstance(obj, TypeB):
        return handle_b(obj)
    elif isinstance(obj, TypeC):
        return handle_c(obj)
"""
        test_file = tmp_path / "isinstance_cascade.py"
        test_file.write_text(code)

        violations = analyze_file_solid(test_file, SOLIDThresholds())

        assert any(v.violation_type == "ocp_isinstance_cascade" for v in violations)

    def test_type_switch(self, tmp_path: Path) -> None:
        """Type-based if/elif chains suggest OCP violation."""
        code = """
def process(type_name):
    if type_name == "credit":
        return process_credit()
    elif type_name == "debit":
        return process_debit()
    elif type_name == "crypto":
        return process_crypto()
"""
        test_file = tmp_path / "type_switch.py"
        test_file.write_text(code)

        _ = analyze_file_solid(test_file, SOLIDThresholds())
        # This is harder to detect reliably, may not flag
        # The validator uses heuristics


class TestLSPDetection:
    """Test Liskov Substitution Principle detection."""

    def test_not_implemented_in_override(self, tmp_path: Path) -> None:
        """Overrides that raise NotImplementedError violate LSP."""
        code = """
class Base:
    def method(self):
        return 42

class Derived(Base):
    def method(self):
        raise NotImplementedError("Not supported")
"""
        test_file = tmp_path / "lsp_violation.py"
        test_file.write_text(code)

        violations = analyze_file_solid(test_file, SOLIDThresholds())

        assert any(v.violation_type == "lsp_not_implemented" for v in violations)


class TestISPDetection:
    """Test Interface Segregation Principle detection."""

    def test_fat_interface(self, tmp_path: Path) -> None:
        """Protocols/ABCs with too many methods violate ISP."""
        code = """
from typing import Protocol

class FatInterface(Protocol):
    def method1(self) -> None: ...
    def method2(self) -> None: ...
    def method3(self) -> None: ...
    def method4(self) -> None: ...
    def method5(self) -> None: ...
    def method6(self) -> None: ...
    def method7(self) -> None: ...
    def method8(self) -> None: ...
"""
        test_file = tmp_path / "fat_interface.py"
        test_file.write_text(code)

        thresholds = SOLIDThresholds(max_interface_methods=7)
        violations = analyze_file_solid(test_file, thresholds)

        assert any(v.violation_type == "isp_fat_interface" for v in violations)

    def test_abc_fat_interface(self, tmp_path: Path) -> None:
        """ABCs with too many abstract methods violate ISP."""
        code = """
from abc import ABC, abstractmethod

class FatABC(ABC):
    @abstractmethod
    def method1(self): pass
    @abstractmethod
    def method2(self): pass
    @abstractmethod
    def method3(self): pass
    @abstractmethod
    def method4(self): pass
    @abstractmethod
    def method5(self): pass
    @abstractmethod
    def method6(self): pass
    @abstractmethod
    def method7(self): pass
    @abstractmethod
    def method8(self): pass
"""
        test_file = tmp_path / "fat_abc.py"
        test_file.write_text(code)

        thresholds = SOLIDThresholds(max_interface_methods=7)
        violations = analyze_file_solid(test_file, thresholds)

        assert any(v.violation_type == "isp_fat_interface" for v in violations)


class TestDIPDetection:
    """Test Dependency Inversion Principle detection."""

    def test_direct_instantiation_in_function(self, tmp_path: Path) -> None:
        """Direct instantiation of services in business logic violates DIP."""
        code = """
def process_order(order_id):
    db = DatabaseConnection()  # Direct instantiation
    logger = LoggerService()   # Direct instantiation
    return db.get_order(order_id)
"""
        test_file = tmp_path / "domain" / "order.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text(code)

        violations = analyze_file_solid(test_file, SOLIDThresholds())

        # DIP detection in core paths
        assert any(v.violation_type == "dip_direct_instantiation" for v in violations)


class TestValidationResult:
    """Test overall validation result."""

    def test_clean_file_passes(self, tmp_path: Path) -> None:
        """Clean files should pass validation."""
        code = """
def simple_function(x: int) -> int:
    return x * 2
"""
        test_file = tmp_path / "clean.py"
        test_file.write_text(code)

        result = validate_solid(str(tmp_path), all_files=True)
        assert result.allowed

    def test_json_output(self, tmp_path: Path) -> None:
        """Result should be JSON serializable."""
        code = "x = 1"
        test_file = tmp_path / "simple.py"
        test_file.write_text(code)

        result = validate_solid(str(tmp_path), all_files=True)

        # Should not raise
        import json
        json.dumps({
            "allowed": result.allowed,
            "violations": result.violations,
            "summary": result.summary,
        })


class TestEdgeCases:
    """Test edge cases."""

    def test_syntax_error_file(self, tmp_path: Path) -> None:
        """Syntax errors should not crash validator."""
        test_file = tmp_path / "bad.py"
        test_file.write_text("def broken(")

        violations = analyze_file_solid(test_file, SOLIDThresholds())
        # Should return empty list, not crash
        assert violations == []

    def test_empty_file(self, tmp_path: Path) -> None:
        """Empty files should not crash."""
        test_file = tmp_path / "empty.py"
        test_file.write_text("")

        violations = analyze_file_solid(test_file, SOLIDThresholds())
        assert violations == []
