#!/usr/bin/env python3
"""
SuperClaude CI/CD Setup Generator

Generates GitHub Actions workflows and pre-commit configuration
from Jinja2 templates based on detected project type.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

try:
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    Environment = None
    FileSystemLoader = None


def detect_project_type(project_path: Path) -> Optional[str]:
    """Detect project type from manifest files."""
    detectors = {
        "python": ["pyproject.toml", "setup.py", "requirements.txt"],
        "node": ["package.json"],
        "go": ["go.mod"],
        "rust": ["Cargo.toml"],
    }

    for lang, files in detectors.items():
        for file in files:
            if (project_path / file).exists():
                return lang
    return None


def detect_main_branch(project_path: Path) -> str:
    """Detect the main branch name from git config or HEAD."""
    git_head = project_path / ".git" / "HEAD"
    if git_head.exists():
        content = git_head.read_text().strip()
        if content.startswith("ref: refs/heads/"):
            return content.replace("ref: refs/heads/", "")

    # Check common branch names
    git_refs = project_path / ".git" / "refs" / "heads"
    if git_refs.exists():
        if (git_refs / "main").exists():
            return "main"
        if (git_refs / "master").exists():
            return "master"

    return "main"


def detect_python_config(project_path: Path) -> "dict[str, Any]":
    """Detect Python project configuration."""
    config = {
        "python_versions": ["3.10", "3.11", "3.12"],
        "source_dir": "src",
        "package_name": project_path.name,
        "coverage_threshold": 90,
        "codecov": True,
        "mypy_non_blocking": True,
        "type_stubs": ["types-PyYAML", "types-requests"],
    }

    pyproject = project_path / "pyproject.toml"
    if pyproject.exists():
        try:
            import tomllib

            with open(pyproject, "rb") as f:
                data = tomllib.load(f)

            # Get package name
            if "project" in data and "name" in data["project"]:
                config["package_name"] = data["project"]["name"]

            # Detect source directory
            if (project_path / "src").is_dir():
                config["source_dir"] = "src"
            elif (project_path / config["package_name"]).is_dir():
                config["source_dir"] = config["package_name"]

            # Get Python version requirements
            if "project" in data and "requires-python" in data["project"]:
                req = data["project"]["requires-python"]
                # Parse minimum version
                if ">=" in req:
                    min_ver = req.split(">=")[1].strip().split(",")[0]
                    # Adjust version list based on minimum
                    if min_ver.startswith("3.11"):
                        config["python_versions"] = ["3.11", "3.12"]
                    elif min_ver.startswith("3.12"):
                        config["python_versions"] = ["3.12"]

        except Exception:
            pass  # Graceful fallback to default config if parsing fails

    return config


def detect_node_config(project_path: Path) -> "dict[str, Any]":
    """Detect Node.js project configuration."""
    config = {
        "node_versions": ["18", "20", "22"],
        "package_manager": "npm",
        "typescript": False,
        "codecov": True,
    }

    package_json = project_path / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text())

            # Detect package manager
            if (project_path / "pnpm-lock.yaml").exists():
                config["package_manager"] = "pnpm"
            elif (project_path / "yarn.lock").exists():
                config["package_manager"] = "yarn"
            elif (project_path / "package-lock.json").exists():
                config["package_manager"] = "npm"

            # Detect TypeScript
            if "typescript" in data.get("devDependencies", {}):
                config["typescript"] = True
            if (project_path / "tsconfig.json").exists():
                config["typescript"] = True

            # Get project name
            if "name" in data:
                config["project_name"] = data["name"]

        except Exception:
            pass  # Graceful fallback to default config if parsing fails

    return config


def detect_go_config(project_path: Path) -> "dict[str, Any]":
    """Detect Go project configuration."""
    config = {
        "go_versions": ["1.21", "1.22"],
        "codecov": True,
    }

    go_mod = project_path / "go.mod"
    if go_mod.exists():
        try:
            content = go_mod.read_text()
            for line in content.splitlines():
                if line.startswith("go "):
                    version = line.split()[1]
                    major_minor = ".".join(version.split(".")[:2])
                    # Include current and next version
                    next_minor = str(int(major_minor.split(".")[1]) + 1)
                    next_version = f"{major_minor.split('.')[0]}.{next_minor}"
                    config["go_versions"] = [major_minor, next_version]
                    break
        except Exception:
            pass  # Graceful fallback to default config if parsing fails

    return config


def detect_rust_config(project_path: Path) -> "dict[str, Any]":
    """Detect Rust project configuration."""
    config = {
        "rust_channel": "stable",
        "msrv": None,
        "codecov": True,
    }

    cargo_toml = project_path / "Cargo.toml"
    if cargo_toml.exists():
        try:
            content = cargo_toml.read_text()
            for line in content.splitlines():
                if "rust-version" in line:
                    # Extract MSRV
                    msrv = line.split("=")[1].strip().strip('"').strip("'")
                    config["msrv"] = msrv
                    break
        except Exception:
            pass  # Graceful fallback to default config if parsing fails

    return config


def get_template_context(
    project_path: Path, lang: str, full: bool = False, minimal: bool = False
) -> "dict[str, Any]":
    """Build template context for the given language."""
    context = {
        "project_name": project_path.name,
        "main_branch": detect_main_branch(project_path),
        "generated_at": datetime.now().isoformat(),
        "minimal": minimal,
        "full": full,
    }

    if lang == "python":
        context.update(detect_python_config(project_path))
    elif lang == "node":
        context.update(detect_node_config(project_path))
    elif lang == "go":
        context.update(detect_go_config(project_path))
    elif lang == "rust":
        context.update(detect_rust_config(project_path))

    return context


def get_templates_to_generate(lang: str, minimal: bool, full: bool) -> "list[tuple[str, str]]":
    """Get list of (template_name, output_path) tuples."""
    templates = []

    # Always include CI
    templates.append((f"{lang}/ci.yml.j2", ".github/workflows/ci.yml"))

    if not minimal:
        # Security workflow
        templates.append((f"{lang}/security.yml.j2", ".github/workflows/security.yml"))

        # AI review
        templates.append((f"{lang}/ai-review.yml.j2", ".github/workflows/ai-review.yml"))

        # Pre-commit config
        templates.append((f"{lang}/pre-commit-config.yaml.j2", ".pre-commit-config.yaml"))

    if full:
        # Publish workflow (if available for this language)
        publish_template = f"{lang}/publish.yml.j2"
        templates.append((publish_template, ".github/workflows/publish.yml"))

    return templates


def check_conflicts(project_path: Path, output_files: "list[str]") -> "list[str]":
    """Check for existing files that would be overwritten."""
    conflicts = []
    for output_file in output_files:
        full_path = project_path / output_file
        if full_path.exists():
            conflicts.append(output_file)
    return conflicts


def backup_file(file_path: Path) -> Path:
    """Create a backup of an existing file."""
    backup_dir = file_path.parent / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
    backup_path = backup_dir / backup_name

    shutil.copy2(file_path, backup_path)
    return backup_path


def generate_workflows(
    project_path: Path,
    templates_path: Path,
    lang: str,
    context: "dict[str, Any]",
    templates: "list[tuple[str, str]]",
    force: bool = False,
) -> "dict[str, Any]":
    """Generate workflow files from templates."""
    if Environment is None:
        return {
            "success": False,
            "error": "Jinja2 is not installed. Run: pip install jinja2",
            "created": [],
            "backed_up": [],
        }

    env = Environment(
        loader=FileSystemLoader(str(templates_path)),
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=True,
    )

    created = []
    backed_up = []
    errors = []

    for template_name, output_file in templates:
        output_path = project_path / output_file

        try:
            # Check if template exists
            template_file = templates_path / template_name
            if not template_file.exists():
                errors.append(f"Template not found: {template_name}")
                continue

            # Backup existing file if needed
            if output_path.exists():
                if force:
                    backup_path = backup_file(output_path)
                    backed_up.append((output_file, str(backup_path)))
                else:
                    errors.append(f"File exists (use --force to overwrite): {output_file}")
                    continue

            # Ensure directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Render template
            template = env.get_template(template_name)
            content = template.render(**context)

            # Write output
            output_path.write_text(content)
            created.append(output_file)

        except Exception as e:
            errors.append(f"Error generating {output_file}: {e}")

    return {
        "success": len(errors) == 0,
        "created": created,
        "backed_up": backed_up,
        "errors": errors,
    }


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate CI/CD workflows")
    parser.add_argument(
        "--project-path",
        type=Path,
        default=Path.cwd(),
        help="Path to project root",
    )
    parser.add_argument(
        "--templates-path",
        type=Path,
        help="Path to templates directory",
    )
    parser.add_argument(
        "--lang",
        choices=["python", "node", "go", "rust"],
        help="Force project language",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files",
    )
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="Generate minimal CI only",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Generate all workflows including publish",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing files",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    # Detect or use specified language
    lang = args.lang or detect_project_type(args.project_path)
    if not lang:
        result = {
            "success": False,
            "error": "Could not detect project type. Use --lang to specify.",
        }
        print(json.dumps(result) if args.json else result["error"])
        return 1

    # Find templates path
    templates_path = args.templates_path
    if not templates_path:
        # Look for templates relative to this script
        script_dir = Path(__file__).parent.parent.parent.parent.parent
        templates_path = script_dir / "templates" / "workflows"

    if not templates_path.exists():
        result = {
            "success": False,
            "error": f"Templates directory not found: {templates_path}",
        }
        print(json.dumps(result) if args.json else result["error"])
        return 1

    # Build context
    context = get_template_context(args.project_path, lang, args.full, args.minimal)

    # Get templates to generate
    templates = get_templates_to_generate(lang, args.minimal, args.full)

    # Check for conflicts
    output_files = [t[1] for t in templates]
    conflicts = check_conflicts(args.project_path, output_files)

    if args.dry_run:
        result = {
            "success": True,
            "dry_run": True,
            "language": lang,
            "would_create": output_files,
            "conflicts": conflicts,
            "context": context,
        }
        print(json.dumps(result, indent=2) if args.json else str(result))
        return 0

    if conflicts and not args.force:
        result = {
            "success": False,
            "error": "Existing files would be overwritten. Use --force to proceed.",
            "conflicts": conflicts,
        }
        print(json.dumps(result, indent=2) if args.json else result["error"])
        return 1

    # Generate workflows
    result = generate_workflows(
        args.project_path,
        templates_path,
        lang,
        context,
        templates,
        args.force,
    )
    result["language"] = lang

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["success"]:
            print(f"Successfully generated {len(result['created'])} files:")
            for f in result["created"]:
                print(f"  - {f}")
            if result["backed_up"]:
                print("\nBacked up existing files:")
                for orig, backup in result["backed_up"]:
                    print(f"  - {orig} -> {backup}")
        else:
            print("Errors occurred:")
            for e in result.get("errors", []):
                print(f"  - {e}")

    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit(main())
