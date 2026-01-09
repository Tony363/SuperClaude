#!/usr/bin/env python3
"""Framework Detector - Auto-detect testing framework and command.

Detects testing frameworks using CI-first strategy:
1. Check CI config files (GitHub Actions, GitLab CI)
2. Check package manifests (package.json, pyproject.toml, etc.)
3. Check framework config files (jest.config.js, pytest.ini)

Supports: pytest, jest, vitest, go test, cargo test

Exit Codes:
    0 - Framework detected successfully
    2 - No framework detected
    3 - Multiple frameworks detected (ambiguous)
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class FrameworkInfo:
    """Detected framework information."""
    name: str  # pytest, jest, vitest, go, cargo
    test_command: str  # Full command template
    targeted_template: str  # Command for running single test file
    config_source: str  # Where detection came from


class FrameworkDetector:
    """Auto-detect testing framework for a scope."""

    # Framework signatures
    PYTEST_PATTERNS = [
        r"pytest",
        r"py\.test",
        r"python -m pytest"
    ]
    JEST_PATTERNS = [
        r"jest",
        r"npm (?:run )?test",
        r"yarn test"
    ]
    VITEST_PATTERNS = [
        r"vitest",
        r"npm (?:run )?vitest",
        r"yarn vitest"
    ]
    GO_PATTERNS = [
        r"go test",
    ]
    CARGO_PATTERNS = [
        r"cargo test",
    ]

    def __init__(self, scope_root: Path):
        """Initialize detector.

        Args:
            scope_root: Root directory to search
        """
        self.scope_root = Path(scope_root)

    def detect(self) -> Optional[FrameworkInfo]:
        """Detect testing framework.

        Returns:
            FrameworkInfo if detected, None otherwise
        """
        # Strategy 1: CI configs (highest priority)
        result = self._detect_from_ci()
        if result:
            return result

        # Strategy 2: Package manifests
        result = self._detect_from_manifests()
        if result:
            return result

        # Strategy 3: Framework config files
        result = self._detect_from_configs()
        if result:
            return result

        return None

    def _detect_from_ci(self) -> Optional[FrameworkInfo]:
        """Detect from CI configuration files."""
        ci_files = [
            ".github/workflows/*.yml",
            ".github/workflows/*.yaml",
            ".gitlab-ci.yml",
            ".circleci/config.yml"
        ]

        for pattern in ci_files:
            for ci_file in self.scope_root.glob(pattern):
                if not ci_file.is_file():
                    continue

                try:
                    content = ci_file.read_text()

                    # Try to extract test command
                    # Look for common patterns like "run: pytest" or "script: jest"
                    for line in content.split("\n"):
                        if "run:" in line or "script:" in line:
                            # pytest
                            if any(re.search(p, line, re.IGNORECASE) for p in self.PYTEST_PATTERNS):
                                return FrameworkInfo(
                                    name="pytest",
                                    test_command="pytest",
                                    targeted_template="pytest {test_file}",
                                    config_source=f"CI:{ci_file.name}"
                                )
                            # jest
                            if any(re.search(p, line, re.IGNORECASE) for p in self.JEST_PATTERNS):
                                return FrameworkInfo(
                                    name="jest",
                                    test_command="npm test",
                                    targeted_template="jest {test_file}",
                                    config_source=f"CI:{ci_file.name}"
                                )
                            # vitest
                            if any(re.search(p, line, re.IGNORECASE) for p in self.VITEST_PATTERNS):
                                return FrameworkInfo(
                                    name="vitest",
                                    test_command="vitest run",
                                    targeted_template="vitest run {test_file}",
                                    config_source=f"CI:{ci_file.name}"
                                )
                            # go test
                            if any(re.search(p, line, re.IGNORECASE) for p in self.GO_PATTERNS):
                                return FrameworkInfo(
                                    name="go",
                                    test_command="go test ./...",
                                    targeted_template="go test {test_file}",
                                    config_source=f"CI:{ci_file.name}"
                                )
                            # cargo test
                            if any(re.search(p, line, re.IGNORECASE) for p in self.CARGO_PATTERNS):
                                return FrameworkInfo(
                                    name="cargo",
                                    test_command="cargo test",
                                    targeted_template="cargo test --test {test_file}",
                                    config_source=f"CI:{ci_file.name}"
                                )
                except (OSError, UnicodeDecodeError):
                    continue

        return None

    def _detect_from_manifests(self) -> Optional[FrameworkInfo]:
        """Detect from package manifest files."""
        # Python: pyproject.toml, setup.py, requirements-dev.txt
        pyproject = self.scope_root / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()
                if "pytest" in content or "[tool.pytest" in content:
                    return FrameworkInfo(
                        name="pytest",
                        test_command="pytest",
                        targeted_template="pytest {test_file}",
                        config_source="pyproject.toml"
                    )
            except (OSError, UnicodeDecodeError):
                pass

        # JavaScript/TypeScript: package.json
        package_json = self.scope_root / "package.json"
        if package_json.exists():
            try:
                content = package_json.read_text()
                data = json.loads(content)

                # Check scripts
                scripts = data.get("scripts", {})
                test_script = scripts.get("test", "")

                if "jest" in test_script or "jest" in data.get("devDependencies", {}):
                    return FrameworkInfo(
                        name="jest",
                        test_command="npm test",
                        targeted_template="jest {test_file}",
                        config_source="package.json"
                    )

                if "vitest" in test_script or "vitest" in data.get("devDependencies", {}):
                    return FrameworkInfo(
                        name="vitest",
                        test_command="vitest run",
                        targeted_template="vitest run {test_file}",
                        config_source="package.json"
                    )
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                pass

        # Go: go.mod
        go_mod = self.scope_root / "go.mod"
        if go_mod.exists():
            return FrameworkInfo(
                name="go",
                test_command="go test ./...",
                targeted_template="go test {test_file}",
                config_source="go.mod"
            )

        # Rust: Cargo.toml
        cargo_toml = self.scope_root / "Cargo.toml"
        if cargo_toml.exists():
            return FrameworkInfo(
                name="cargo",
                test_command="cargo test",
                targeted_template="cargo test --test {test_file}",
                config_source="Cargo.toml"
            )

        return None

    def _detect_from_configs(self) -> Optional[FrameworkInfo]:
        """Detect from framework config files."""
        # pytest
        pytest_configs = [
            "pytest.ini",
            "pyproject.toml",
            "tox.ini",
            "setup.cfg"
        ]
        for config in pytest_configs:
            if (self.scope_root / config).exists():
                return FrameworkInfo(
                    name="pytest",
                    test_command="pytest",
                    targeted_template="pytest {test_file}",
                    config_source=config
                )

        # jest
        jest_configs = [
            "jest.config.js",
            "jest.config.ts",
            "jest.config.json"
        ]
        for config in jest_configs:
            if (self.scope_root / config).exists():
                return FrameworkInfo(
                    name="jest",
                    test_command="npm test",
                    targeted_template="jest {test_file}",
                    config_source=config
                )

        # vitest
        vitest_configs = [
            "vitest.config.js",
            "vitest.config.ts"
        ]
        for config in vitest_configs:
            if (self.scope_root / config).exists():
                return FrameworkInfo(
                    name="vitest",
                    test_command="vitest run",
                    targeted_template="vitest run {test_file}",
                    config_source=config
                )

        return None


def detect_scope_root(start_path: Path) -> Optional[Path]:
    """Detect scope root by finding nearest manifest.

    Looks for:
    - pyproject.toml, setup.py (Python)
    - package.json (JavaScript/TypeScript)
    - go.mod (Go)
    - Cargo.toml (Rust)
    - pom.xml, build.gradle (Java)

    Args:
        start_path: Starting directory

    Returns:
        Path to scope root or None
    """
    manifests = [
        "pyproject.toml",
        "setup.py",
        "package.json",
        "go.mod",
        "Cargo.toml",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts"
    ]

    current = Path(start_path).resolve()

    # Search up to repository root (contains .git)
    while current != current.parent:
        for manifest in manifests:
            if (current / manifest).exists():
                return current

        # Stop at repository root
        if (current / ".git").exists():
            return current

        current = current.parent

    return None


def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Detect testing framework")
    parser.add_argument("--scope-root", help="Scope root directory (if known)")
    parser.add_argument("--detect-scope", help="Detect scope root from this path")
    parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    if args.detect_scope:
        # Detect scope root
        scope_root = detect_scope_root(Path(args.detect_scope))
        if scope_root:
            output = {
                "success": True,
                "scope_root": str(scope_root),
                "message": f"Detected scope root: {scope_root}"
            }
            print(json.dumps(output, indent=2) if args.json else output["message"])
            sys.exit(0)
        else:
            output = {
                "success": False,
                "error": "No scope root detected"
            }
            print(json.dumps(output, indent=2) if args.json else output["error"])
            sys.exit(2)

    if not args.scope_root:
        print("Error: --scope-root or --detect-scope required", file=sys.stderr)
        sys.exit(3)

    # Detect framework
    detector = FrameworkDetector(Path(args.scope_root))
    framework = detector.detect()

    if framework:
        output = {
            "success": True,
            "framework": framework.name,
            "test_command": framework.test_command,
            "targeted_template": framework.targeted_template,
            "config_source": framework.config_source
        }
        print(json.dumps(output, indent=2))
        sys.exit(0)
    else:
        output = {
            "success": False,
            "error": "No testing framework detected"
        }
        print(json.dumps(output, indent=2) if args.json else output["error"])
        sys.exit(2)


if __name__ == "__main__":
    main()
