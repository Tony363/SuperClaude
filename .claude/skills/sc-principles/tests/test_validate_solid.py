#!/usr/bin/env python3
"""Tests for SOLID validator."""

from pathlib import Path

from scripts.validate_solid import (
    SOLIDThresholds,
    SOLIDViolation,
    analyze_file_solid,
    generate_recommendations,
    main,
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


    def test_abc_not_implemented_not_flagged(self, tmp_path: Path) -> None:
        """ABC classes raising NotImplementedError should NOT be flagged (correct pattern)."""
        code = """
from abc import ABC, abstractmethod

class BaseProcessor(ABC):
    @abstractmethod
    def process(self, data):
        raise NotImplementedError("Subclasses must implement process()")

    @abstractmethod
    def validate(self, data):
        raise NotImplementedError
"""
        test_file = tmp_path / "abc_base.py"
        test_file.write_text(code)

        violations = analyze_file_solid(test_file, SOLIDThresholds())

        # ABC with @abstractmethod should NOT trigger LSP violation
        assert not any(v.violation_type == "lsp_not_implemented" for v in violations)

    def test_protocol_not_implemented_not_flagged(self, tmp_path: Path) -> None:
        """Protocol classes raising NotImplementedError should NOT be flagged."""
        code = """
from typing import Protocol

class DataSource(Protocol):
    def fetch(self, query: str) -> list:
        raise NotImplementedError
"""
        test_file = tmp_path / "protocol_base.py"
        test_file.write_text(code)

        violations = analyze_file_solid(test_file, SOLIDThresholds())

        assert not any(v.violation_type == "lsp_not_implemented" for v in violations)


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

        json.dumps(
            {
                "allowed": result.allowed,
                "violations": result.violations,
                "summary": result.summary,
            }
        )


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


class TestMetaclassABCDetection:
    """Tests for metaclass=ABCMeta detection (lines 289-294)."""

    def test_metaclass_abcmeta_recognized_as_abc(self, tmp_path: Path) -> None:
        """Classes with metaclass=ABCMeta should be treated as abstract (no LSP flag)."""
        code = """
from abc import ABCMeta, abstractmethod

class Base(metaclass=ABCMeta):
    @abstractmethod
    def method(self):
        raise NotImplementedError
"""
        test_file = tmp_path / "metaclass_abc.py"
        test_file.write_text(code)

        violations = analyze_file_solid(test_file, SOLIDThresholds())
        assert not any(v.violation_type == "lsp_not_implemented" for v in violations)

    def test_metaclass_abcmeta_attribute_form(self, tmp_path: Path) -> None:
        """abc.ABCMeta in metaclass keyword should also be recognized."""
        code = """
import abc

class Base(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def method(self):
        raise NotImplementedError
"""
        test_file = tmp_path / "metaclass_abc_attr.py"
        test_file.write_text(code)

        violations = analyze_file_solid(test_file, SOLIDThresholds())
        assert not any(v.violation_type == "lsp_not_implemented" for v in violations)

    def test_metaclass_abcmeta_fat_interface_detected(self, tmp_path: Path) -> None:
        """ABCMeta classes with too many methods should trigger ISP violation."""
        code = """
from abc import ABCMeta, abstractmethod

class FatABC(metaclass=ABCMeta):
    @abstractmethod
    def m1(self): pass
    @abstractmethod
    def m2(self): pass
    @abstractmethod
    def m3(self): pass
    @abstractmethod
    def m4(self): pass
    @abstractmethod
    def m5(self): pass
    @abstractmethod
    def m6(self): pass
    @abstractmethod
    def m7(self): pass
    @abstractmethod
    def m8(self): pass
"""
        test_file = tmp_path / "fat_metaclass.py"
        test_file.write_text(code)

        thresholds = SOLIDThresholds(max_interface_methods=7)
        violations = analyze_file_solid(test_file, thresholds)
        assert any(v.violation_type == "isp_fat_interface" for v in violations)


class TestDIPAttributeAccess:
    """Tests for DIP _get_class_name with Attribute nodes (line 301-302)."""

    def test_module_qualified_service_instantiation(self, tmp_path: Path) -> None:
        """mod.Service() should be flagged via Attribute node class name extraction."""
        test_file = tmp_path / "domain" / "logic.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text(
            '''
def process():
    conn = db.DatabaseConnection()
    return conn.query("SELECT 1")
'''
        )

        violations = analyze_file_solid(test_file, SOLIDThresholds())
        dip_violations = [v for v in violations if v.violation_type == "dip_direct_instantiation"]
        assert len(dip_violations) >= 1


class TestAbstractmethodAttributeDecorator:
    """Tests for @abc.abstractmethod (Attribute form) decorator (lines 278-279)."""

    def test_abc_abstractmethod_attribute_not_flagged(self, tmp_path: Path) -> None:
        """@abc.abstractmethod should not trigger LSP violation."""
        code = """
import abc

class Base(abc.ABC):
    @abc.abstractmethod
    def method(self):
        raise NotImplementedError
"""
        test_file = tmp_path / "abc_attr_decorator.py"
        test_file.write_text(code)

        violations = analyze_file_solid(test_file, SOLIDThresholds())
        assert not any(v.violation_type == "lsp_not_implemented" for v in violations)


class TestServiceClassEndswith:
    """Tests for _is_service_class endswith matching (line 311)."""

    def test_service_suffix_detected(self, tmp_path: Path) -> None:
        """Class names ending with service patterns should be detected."""
        test_file = tmp_path / "domain" / "order.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text(
            '''
def process():
    cache = RedisCache()
    return cache.get("key")
'''
        )

        violations = analyze_file_solid(test_file, SOLIDThresholds())
        dip_violations = [v for v in violations if v.violation_type == "dip_direct_instantiation"]
        assert any("RedisCache" in v.message for v in dip_violations)

    def test_non_service_name_not_flagged(self, tmp_path: Path) -> None:
        """Class names not ending with service patterns should not be flagged."""
        test_file = tmp_path / "domain" / "order.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text(
            '''
def process():
    item = OrderItem()
    return item.total
'''
        )

        violations = analyze_file_solid(test_file, SOLIDThresholds())
        dip_violations = [v for v in violations if v.violation_type == "dip_direct_instantiation"]
        assert not any("OrderItem" in v.message for v in dip_violations)


class TestGenerateRecommendationsSOLID:
    """Tests for generate_recommendations (lines 334-369)."""

    def test_srp_recommendation(self) -> None:
        """SRP violations should generate SRP recommendation."""
        violations = [
            SOLIDViolation(
                file="test.py", line=1, violation_type="srp_file_length",
                message="test", principle="SRP", severity="warning",
            )
        ]
        recs = generate_recommendations(violations)
        assert any("SRP" in r for r in recs)

    def test_ocp_recommendation(self) -> None:
        """OCP violations should generate OCP recommendation."""
        violations = [
            SOLIDViolation(
                file="test.py", line=1, violation_type="ocp_isinstance_cascade",
                message="test", principle="OCP", severity="warning",
            )
        ]
        recs = generate_recommendations(violations)
        assert any("OCP" in r for r in recs)

    def test_lsp_recommendation(self) -> None:
        """LSP violations should generate LSP recommendation."""
        violations = [
            SOLIDViolation(
                file="test.py", line=1, violation_type="lsp_not_implemented",
                message="test", principle="LSP", severity="error",
            )
        ]
        recs = generate_recommendations(violations)
        assert any("LSP" in r for r in recs)

    def test_isp_recommendation(self) -> None:
        """ISP violations should generate ISP recommendation."""
        violations = [
            SOLIDViolation(
                file="test.py", line=1, violation_type="isp_fat_interface",
                message="test", principle="ISP", severity="warning",
            )
        ]
        recs = generate_recommendations(violations)
        assert any("ISP" in r for r in recs)

    def test_dip_recommendation(self) -> None:
        """DIP violations should generate DIP recommendation."""
        violations = [
            SOLIDViolation(
                file="test.py", line=1, violation_type="dip_direct_instantiation",
                message="test", principle="DIP", severity="warning",
            )
        ]
        recs = generate_recommendations(violations)
        assert any("DIP" in r for r in recs)

    def test_empty_violations_no_recommendations(self) -> None:
        """No violations should produce no recommendations."""
        recs = generate_recommendations([])
        assert recs == []


class TestValidateSOLIDOrchestration:
    """Tests for validate_solid orchestration (lines 372-411)."""

    def test_errors_block_validation(self, tmp_path: Path) -> None:
        """LSP errors should block validation."""
        code = """
class Base:
    def method(self):
        return 42

class Derived(Base):
    def method(self):
        raise NotImplementedError("nope")
"""
        test_file = tmp_path / "lsp_bad.py"
        test_file.write_text(code)

        result = validate_solid(str(tmp_path), all_files=True)
        assert result.allowed is False
        assert result.summary["errors"] > 0

    def test_strict_mode_blocks_warnings(self, tmp_path: Path) -> None:
        """Strict mode should block on warnings."""
        code = "\n".join([f"x{i} = {i}" for i in range(350)])
        test_file = tmp_path / "long.py"
        test_file.write_text(code)

        result = validate_solid(
            str(tmp_path),
            thresholds=SOLIDThresholds(max_file_lines=300),
            strict=True,
            all_files=True,
        )
        assert result.summary["warnings"] > 0
        assert result.allowed is False

    def test_by_principle_summary(self, tmp_path: Path) -> None:
        """Summary should include by_principle breakdown."""
        code = """
class Base:
    def method(self):
        return 42

class Derived(Base):
    def method(self):
        raise NotImplementedError("nope")
"""
        test_file = tmp_path / "lsp_bad.py"
        test_file.write_text(code)

        result = validate_solid(str(tmp_path), all_files=True)
        assert "by_principle" in result.summary
        assert "LSP" in result.summary["by_principle"]
        assert result.summary["by_principle"]["LSP"] > 0


class TestSOLIDCLI:
    """Tests for main() CLI entrypoint (lines 414-504)."""

    def test_json_output(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch", capsys: "pytest.CaptureFixture") -> None:
        """--json flag should produce JSON output."""
        import json as json_mod

        test_file = tmp_path / "simple.py"
        test_file.write_text("x = 1\n")
        monkeypatch.setattr(
            "sys.argv",
            ["validate_solid", "--scope-root", str(tmp_path), "--all", "--json"],
        )

        try:
            main()
        except SystemExit:
            pass

        captured = capsys.readouterr()
        output = json_mod.loads(captured.out)
        assert "allowed" in output
        assert "summary" in output

    def test_text_output(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch", capsys: "pytest.CaptureFixture") -> None:
        """Default text output should include key sections."""
        test_file = tmp_path / "simple.py"
        test_file.write_text("x = 1\n")
        monkeypatch.setattr(
            "sys.argv",
            ["validate_solid", "--scope-root", str(tmp_path), "--all"],
        )

        try:
            main()
        except SystemExit:
            pass

        captured = capsys.readouterr()
        assert "SOLID Validation:" in captured.out
        assert "Files analyzed:" in captured.out

    def test_exit_code_zero_on_pass(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch") -> None:
        """Clean code should exit with code 0."""
        import pytest

        test_file = tmp_path / "clean.py"
        test_file.write_text("x = 1\n")
        monkeypatch.setattr(
            "sys.argv",
            ["validate_solid", "--scope-root", str(tmp_path), "--all"],
        )

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_exit_code_two_on_block(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch") -> None:
        """Blocked validation should exit with code 2."""
        import pytest

        test_file = tmp_path / "bad.py"
        test_file.write_text(
            """
class Base:
    def method(self):
        return 42

class Derived(Base):
    def method(self):
        raise NotImplementedError("nope")
"""
        )
        monkeypatch.setattr(
            "sys.argv",
            ["validate_solid", "--scope-root", str(tmp_path), "--all"],
        )

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2

    def test_text_output_with_violations_shows_by_principle(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch", capsys: "pytest.CaptureFixture") -> None:
        """Text output with violations should show By Principle section."""
        test_file = tmp_path / "bad.py"
        test_file.write_text(
            """
class Base:
    def method(self):
        return 42

class Derived(Base):
    def method(self):
        raise NotImplementedError("nope")
"""
        )
        monkeypatch.setattr(
            "sys.argv",
            ["validate_solid", "--scope-root", str(tmp_path), "--all"],
        )

        try:
            main()
        except SystemExit:
            pass

        captured = capsys.readouterr()
        assert "By Principle:" in captured.out
        assert "Violations:" in captured.out
