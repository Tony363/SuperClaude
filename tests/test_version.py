"""
Test version handling and consistency across the framework.
"""

import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_version_import():
    """Test that version can be imported from the package."""
    from SuperClaude import __version__
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_version_format():
    """Test that version follows semantic versioning format."""
    from SuperClaude import __version__
    parts = __version__.split('.')
    assert len(parts) >= 2  # At least major.minor

    # Check that each part is numeric
    for part in parts[:3]:  # Check major, minor, patch if present
        assert part.isdigit(), f"Version part '{part}' is not numeric"


def test_version_consistency():
    """Test that version is consistent across different sources."""
    from SuperClaude import __version__ as package_version

    # Check VERSION file
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.exists():
        file_version = version_file.read_text().strip()
        assert package_version == file_version, \
            f"Package version {package_version} doesn't match VERSION file {file_version}"

    # Check pyproject.toml
    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        # Simple regex to find version in pyproject.toml
        import re
        match = re.search(r'version\s*=\s*"([^"]+)"', content)
        if match:
            pyproject_version = match.group(1)
            assert package_version == pyproject_version, \
                f"Package version {package_version} doesn't match pyproject.toml {pyproject_version}"


def test_version_current():
    """Test that version is the expected current version."""
    from SuperClaude import __version__
    assert __version__ == "4.1.0", f"Expected version 4.1.0, got {__version__}"


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])