import json
from pathlib import Path

from setup import __version__
from setup.components.core import CoreComponent
from setup.components.modes import ModesComponent


def _write_metadata(install_dir: Path, component: str, files):
    metadata = {
        "framework": {
            "version": __version__,
            "name": "SuperClaude",
            "description": "Test framework",
        },
        "components": {
            component: {
                "version": __version__,
                "category": component,
                "files": files,
                "files_count": len(files),
                "installed": True,
            }
        },
    }
    (install_dir / ".superclaude-metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )


def test_core_validate_uses_manifest(tmp_path):
    manifest_files = ["AGENTS.md", "RULES.md"]
    _write_metadata(tmp_path, "core", manifest_files)
    for filename in manifest_files:
        (tmp_path / filename).write_text("stub", encoding="utf-8")

    component = CoreComponent(install_dir=tmp_path)
    success, errors = component.validate_installation()

    assert success, errors


def test_modes_validate_uses_manifest(tmp_path):
    manifest_files = ["MODE_Normal.md", "MODE_Task_Management.md"]
    _write_metadata(tmp_path, "modes", manifest_files)
    for filename in manifest_files:
        (tmp_path / filename).write_text("stub", encoding="utf-8")

    component = ModesComponent(install_dir=tmp_path)
    success, errors = component.validate_installation()

    assert success, errors
