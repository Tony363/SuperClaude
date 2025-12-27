"""
Test version handling and consistency across the framework.

These tests require the archived SDK to be properly installed.
Skip if the archived SDK compatibility layer has import issues.
"""

import json
import re
import sys
import warnings
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Check if archived SDK imports work - skip entire module if not
try:
    from SuperClaude import __version__  # noqa: F401
except ImportError:
    pytest.skip(
        "Archived SDK compatibility layer not available",
        allow_module_level=True,
    )


def test_version_import():
    """Test that version can be imported from the package."""
    from SuperClaude import __version__

    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_version_format():
    """Test that version follows semantic versioning format (with optional pre-release tag)."""
    from SuperClaude import __version__

    semver_pattern = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
    assert semver_pattern.match(__version__), (
        f"Version '{__version__}' does not follow semantic versioning with optional pre-release"
    )


def test_version_consistency():
    """Test that version is consistent across different sources."""
    from SuperClaude import __version__ as package_version

    project_root = Path(__file__).parent.parent
    failures = []
    soft_warnings = []

    version_file = project_root / "VERSION"
    if version_file.exists():
        file_version = version_file.read_text().strip()
        if package_version != file_version:
            failures.append(
                f"VERSION file mismatch: expected {package_version}, found {file_version}"
            )

    pyproject = project_root / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        match = re.search(r'version\s*=\s*"([^"]+)"', content)
        if match and package_version != match.group(1):
            failures.append(
                f"pyproject.toml mismatch: expected {package_version}, found {match.group(1)}"
            )

    package_json = project_root / "package.json"
    if package_json.exists():
        pkg_version = json.loads(package_json.read_text()).get("version")
        if pkg_version and package_version != pkg_version:
            failures.append(
                f"package.json mismatch: expected {package_version}, found {pkg_version}"
            )

    readme = project_root / "README.md"
    if readme.exists():
        readme_content = readme.read_text()
        expected_readme_header = f"SuperClaude Framework v{package_version}"
        if expected_readme_header not in readme_content:
            soft_warnings.append(
                f"README mismatch: '{expected_readme_header}' not found in README.md"
            )

    changelog = project_root / "CHANGELOG.md"
    if changelog.exists():
        changelog_content = changelog.read_text()
        pattern = rf"^## \[{re.escape(package_version)}\]"
        if not re.search(pattern, changelog_content, re.MULTILINE):
            soft_warnings.append(f"CHANGELOG mismatch: heading '## [{package_version}]' not found")

    for note in soft_warnings:
        warnings.warn(note)

    assert not failures, "Version mismatches detected:\n" + "\n".join(failures)


def test_version_current():
    """Test that version is the expected current version."""
    from SuperClaude import __version__

    expected_version = "6.0.0-alpha"
    assert __version__ == expected_version, (
        f"Expected version {expected_version}, got {__version__}"
    )


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
