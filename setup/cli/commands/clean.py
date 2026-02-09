#!/usr/bin/env python3
"""
SuperClaude Clean Command - Cleanup and Recovery Operations

Provides cleanup functionality for corrupted metadata, cache, and temporary files.
Useful for recovering from failed installations or corrupted state.
"""

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

from setup.services.settings import SettingsService
from setup.utils.logger import get_logger
from setup.utils.ui import (
    confirm,
    display_error,
    display_header,
    display_info,
    display_success,
    display_warning,
)


class CleanCommand:
    """Clean command implementation for SuperClaude CLI."""

    def __init__(self, args: argparse.Namespace):
        """Initialize clean command with parsed arguments."""
        self.args = args
        self.logger = get_logger()
        self.install_dir = args.install_dir
        self.dry_run = args.dry_run
        self.force = args.force
        self.settings_service = SettingsService(self.install_dir)

        # Track what was cleaned
        self.cleaned_items = []
        self.failed_items = []

    def clean_metadata(self) -> bool:
        """Clean corrupted metadata files."""
        metadata_files = [
            self.install_dir / ".superclaude-metadata.json",
            self.install_dir / "settings.json",
            self.install_dir / ".component-registry.json",
        ]

        success = True
        for file_path in metadata_files:
            if not file_path.exists():
                continue

            try:
                # Try to parse the file to check if it's corrupted
                if file_path.suffix == ".json":
                    with open(file_path) as f:
                        json.load(f)

                    # File is valid, check if we should still clean it
                    if not self.args.force:
                        display_info(
                            f"  {file_path.name} is valid, skipping (use --force to clean anyway)"
                        )
                        continue

                # Backup before removing
                if not self.dry_run:
                    backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
                    shutil.copy2(file_path, backup_path)
                    file_path.unlink()
                    self.cleaned_items.append(f"Metadata: {file_path.name}")
                    display_success(f"  Cleaned: {file_path.name} (backup created)")
                else:
                    display_info(f"  [DRY RUN] Would clean: {file_path.name}")

            except json.JSONDecodeError:
                # File is corrupted, definitely clean it
                if not self.dry_run:
                    backup_path = file_path.with_suffix(f"{file_path.suffix}.corrupted")
                    shutil.move(str(file_path), str(backup_path))
                    self.cleaned_items.append(f"Corrupted: {file_path.name}")
                    display_warning(f"  Cleaned corrupted: {file_path.name} (moved to .corrupted)")
                else:
                    display_info(f"  [DRY RUN] Would clean corrupted: {file_path.name}")

            except Exception as e:
                self.failed_items.append(f"{file_path.name}: {e!s}")
                display_error(f"  Failed to clean {file_path.name}: {e}")
                success = False

        return success

    def clean_cache(self) -> bool:
        """Clean cache directories and temporary files."""
        cache_dirs = [
            self.install_dir / "cache",
            self.install_dir / ".cache",
            self.install_dir / "tmp",
            self.install_dir / ".tmp",
            Path.home() / ".cache" / "superclaude",
        ]

        success = True
        for cache_dir in cache_dirs:
            if not cache_dir.exists():
                continue

            try:
                size = sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())
                size_mb = size / (1024 * 1024)

                if not self.dry_run:
                    shutil.rmtree(cache_dir)
                    self.cleaned_items.append(f"Cache: {cache_dir.name} ({size_mb:.1f} MB)")
                    display_success(f"  Cleaned cache: {cache_dir.name} ({size_mb:.1f} MB freed)")
                else:
                    display_info(
                        f"  [DRY RUN] Would clean cache: {cache_dir.name} ({size_mb:.1f} MB)"
                    )

            except Exception as e:
                self.failed_items.append(f"{cache_dir.name}: {e!s}")
                display_error(f"  Failed to clean {cache_dir.name}: {e}")
                success = False

        return success

    def clean_logs(self) -> bool:
        """Clean log files (optionally keep recent logs)."""
        log_dir = self.install_dir / "logs"
        if not log_dir.exists():
            return True

        try:
            log_files = list(log_dir.glob("*.log*"))

            if self.args.keep_recent:
                # Keep logs from last 7 days
                cutoff = datetime.now().timestamp() - (7 * 24 * 3600)
                old_logs = [f for f in log_files if f.stat().st_mtime < cutoff]
            else:
                old_logs = log_files

            if old_logs:
                # Calculate size based on files actually being deleted
                total_size = sum(f.stat().st_size for f in old_logs if f.is_file())
                size_mb = total_size / (1024 * 1024)

                if not self.dry_run:
                    for log_file in old_logs:
                        log_file.unlink()
                    self.cleaned_items.append(f"Logs: {len(old_logs)} files ({size_mb:.1f} MB)")
                    display_success(f"  Cleaned {len(old_logs)} log files ({size_mb:.1f} MB freed)")
                else:
                    display_info(
                        f"  [DRY RUN] Would clean {len(old_logs)} log files ({size_mb:.1f} MB)"
                    )
            else:
                display_info("  No log files to clean")

            return True

        except Exception as e:
            self.failed_items.append(f"logs: {e!s}")
            display_error(f"  Failed to clean logs: {e}")
            return False

    def clean_worktrees(self) -> bool:
        """Clean git worktrees created during development."""
        worktrees_dir = Path.cwd() / ".worktrees"
        if not worktrees_dir.exists():
            return True

        try:
            worktrees = list(worktrees_dir.iterdir())
            if not worktrees:
                display_info("  No worktrees to clean")
                return True

            total_size = 0
            for wt in worktrees:
                if wt.is_dir():
                    total_size += sum(f.stat().st_size for f in wt.rglob("*") if f.is_file())

            size_mb = total_size / (1024 * 1024)

            if not self.dry_run:
                # Clean up git worktrees properly
                import subprocess

                for wt in worktrees:
                    try:
                        subprocess.run(
                            ["git", "worktree", "remove", str(wt), "--force"],
                            capture_output=True,
                            check=False,
                        )
                    except (subprocess.SubprocessError, OSError) as e:
                        # Fallback to direct removal if git command fails
                        self.logger.debug(f"Git worktree remove failed, using fallback: {e}")
                        shutil.rmtree(wt, ignore_errors=True)

                self.cleaned_items.append(f"Worktrees: {len(worktrees)} ({size_mb:.1f} MB)")
                display_success(f"  Cleaned {len(worktrees)} worktrees ({size_mb:.1f} MB freed)")
            else:
                display_info(
                    f"  [DRY RUN] Would clean {len(worktrees)} worktrees ({size_mb:.1f} MB)"
                )

            return True

        except Exception as e:
            self.failed_items.append(f"worktrees: {e!s}")
            display_error(f"  Failed to clean worktrees: {e}")
            return False

    def clean_superclaude(self) -> bool:
        """Clean SuperClaude-specific artifacts (skills, hooks, runtime dirs, metadata).

        Removes:
        - Skill directories matching sc-*/agent-* prefixes or known names
        - Hook files installed by SuperClaude
        - superclaude/ runtime directory
        - feedback/ directory
        - learned_skills.db, hooks.log, superclaude_env_vars.json,
          .superclaude-metadata.json
        """
        success = True

        # -- Skills --
        skills_dir = self.install_dir / "skills"
        if skills_dir.exists():
            sc_prefixes = ("sc-", "agent-")
            known_skill_dirs = ("ask", "ask-multi", "learned", "scripts")

            for item in list(skills_dir.iterdir()):
                if item.is_dir() and (
                    item.name.startswith(sc_prefixes) or item.name in known_skill_dirs
                ):
                    if not self.dry_run:
                        try:
                            shutil.rmtree(item)
                            self.cleaned_items.append(f"Skill: {item.name}")
                            display_success(f"  Removed skill directory: {item.name}")
                        except Exception as e:
                            self.failed_items.append(f"skills/{item.name}: {e!s}")
                            display_error(f"  Failed to remove skill {item.name}: {e}")
                            success = False
                    else:
                        display_info(f"  [DRY RUN] Would remove skill directory: {item.name}")
                elif item.is_file() and item.name == "README.md":
                    if not self.dry_run:
                        item.unlink()
                        self.cleaned_items.append("Skill: README.md")
                    else:
                        display_info("  [DRY RUN] Would remove skills/README.md")

            # Remove skills/ if empty
            if not self.dry_run:
                try:
                    if skills_dir.exists() and not any(skills_dir.iterdir()):
                        skills_dir.rmdir()
                        display_success("  Removed empty skills directory")
                except Exception:
                    pass  # Best-effort cleanup; directory may be in use

        # -- Hooks --
        hooks_dir = self.install_dir / "hooks"
        known_hooks = ("block-destructive-git.sh", "block-dangerous-ops.sh", "auto-format.sh")
        if hooks_dir.exists():
            for hook_name in known_hooks:
                hook_path = hooks_dir / hook_name
                if hook_path.exists():
                    if not self.dry_run:
                        try:
                            hook_path.unlink()
                            self.cleaned_items.append(f"Hook: {hook_name}")
                            display_success(f"  Removed hook: {hook_name}")
                        except Exception as e:
                            self.failed_items.append(f"hooks/{hook_name}: {e!s}")
                            success = False
                    else:
                        display_info(f"  [DRY RUN] Would remove hook: {hook_name}")

            # Remove hooks/ if empty
            if not self.dry_run:
                try:
                    if hooks_dir.exists() and not any(hooks_dir.iterdir()):
                        hooks_dir.rmdir()
                        display_success("  Removed empty hooks directory")
                except Exception:
                    pass  # Best-effort cleanup; directory may be in use

        # -- Directories --
        for dirname in ("superclaude", "feedback", "commands"):
            dir_path = self.install_dir / dirname
            if dir_path.exists() and dir_path.is_dir():
                if not self.dry_run:
                    try:
                        shutil.rmtree(dir_path)
                        self.cleaned_items.append(f"Directory: {dirname}/")
                        display_success(f"  Removed {dirname}/ directory")
                    except Exception as e:
                        self.failed_items.append(f"{dirname}: {e!s}")
                        display_error(f"  Failed to remove {dirname}/: {e}")
                        success = False
                else:
                    display_info(f"  [DRY RUN] Would remove {dirname}/ directory")

        # -- Loose files --
        loose_files = [
            "learned_skills.db",
            "hooks.log",
            "superclaude_env_vars.json",
            ".superclaude-metadata.json",
        ]
        for filename in loose_files:
            file_path = self.install_dir / filename
            if file_path.exists():
                if not self.dry_run:
                    try:
                        file_path.unlink()
                        self.cleaned_items.append(f"File: {filename}")
                        display_success(f"  Removed {filename}")
                    except Exception as e:
                        self.failed_items.append(f"{filename}: {e!s}")
                        display_error(f"  Failed to remove {filename}: {e}")
                        success = False
                else:
                    display_info(f"  [DRY RUN] Would remove {filename}")

        if not self.cleaned_items and not self.dry_run:
            display_info("  No SuperClaude artifacts found to clean")

        return success

    def validate_installation(self) -> bool:
        """Validate installation state after cleaning."""
        display_info("\n🔍 Validating installation state...")

        critical_paths = [
            self.install_dir,
            self.install_dir / "commands",
            self.install_dir / "agents",
        ]

        valid = True
        for path in critical_paths:
            if path.exists():
                display_success(f"  ✓ {path.name} exists")
            else:
                display_warning(f"  ⚠ {path.name} missing (will be created on next install)")
                valid = False

        return valid

    def run(self) -> int:
        """Execute the clean command."""
        display_header("SuperClaude Clean", "Cleanup and Recovery Tool")

        # Determine what to clean
        clean_all = self.args.all or (
            not any(
                [
                    self.args.metadata,
                    self.args.cache,
                    self.args.logs,
                    self.args.worktrees,
                    self.args.superclaude,
                ]
            )
        )

        operations = []
        if clean_all or self.args.metadata:
            operations.append(("metadata files", self.clean_metadata))
        if clean_all or self.args.cache:
            operations.append(("cache directories", self.clean_cache))
        if clean_all or self.args.logs:
            operations.append(("log files", self.clean_logs))
        if clean_all or self.args.worktrees:
            operations.append(("git worktrees", self.clean_worktrees))
        if clean_all or self.args.superclaude:
            operations.append(("SuperClaude artifacts", self.clean_superclaude))

        # Confirm operation
        if not self.force and not self.dry_run:
            display_warning("\n⚠️  This will clean the following:")
            for name, _ in operations:
                display_info(f"  • {name}")

            if not confirm("\nProceed with cleanup?", default=True):
                display_info("Cleanup cancelled")
                return 0

        # Execute cleanup operations
        display_info("\n🧹 Starting cleanup...")
        all_success = True

        for name, operation in operations:
            display_info(f"\nCleaning {name}...")
            if not operation():
                all_success = False

        # Summary
        display_info("\n📊 Cleanup Summary:")
        if self.cleaned_items:
            display_success(f"  Cleaned {len(self.cleaned_items)} items:")
            for item in self.cleaned_items:
                display_info(f"    • {item}")
        else:
            display_info("  Nothing was cleaned")

        if self.failed_items:
            display_error(f"  Failed to clean {len(self.failed_items)} items:")
            for item in self.failed_items:
                display_error(f"    • {item}")

        # Validate if not dry run
        if not self.dry_run and (self.args.validate or clean_all):
            self.validate_installation()

        # Final message
        if all_success:
            if self.dry_run:
                display_info("\n✅ Dry run complete. Use without --dry-run to execute.")
            else:
                display_success("\n✅ Cleanup completed successfully!")
                display_info("Run 'SuperClaude install' to reinitialize if needed.")
            return 0
        else:
            display_error("\n❌ Cleanup completed with errors. Check messages above.")
            return 1


def register_parser(subparsers, global_parser):
    """Register the clean command parser."""
    parser = subparsers.add_parser(
        "clean",
        help="Clean corrupted metadata, cache, and temporary files",
        parents=[global_parser],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
Clean corrupted metadata, cache, and temporary files.

This command helps recover from failed installations, corrupted state,
or to free up disk space by removing temporary files.

Examples:
  SuperClaude clean                    # Clean everything (safe defaults)
  SuperClaude clean --metadata         # Clean only metadata files
  SuperClaude clean --cache --logs     # Clean cache and logs
  SuperClaude clean --dry-run          # Preview what would be cleaned
  SuperClaude clean --force            # Clean even valid metadata files
        """,
    )

    # What to clean
    clean_group = parser.add_argument_group("cleanup targets")
    clean_group.add_argument(
        "--all",
        action="store_true",
        help="Clean everything (default if no targets specified)",
    )
    clean_group.add_argument(
        "--metadata", action="store_true", help="Clean metadata and settings files"
    )
    clean_group.add_argument("--cache", action="store_true", help="Clean cache directories")
    clean_group.add_argument("--logs", action="store_true", help="Clean log files")
    clean_group.add_argument("--worktrees", action="store_true", help="Clean git worktrees")
    clean_group.add_argument(
        "--superclaude",
        action="store_true",
        help="Clean SuperClaude artifacts (skills, hooks, runtime dirs, learned_skills.db)",
    )

    # Options
    options_group = parser.add_argument_group("options")
    options_group.add_argument(
        "--keep-recent", action="store_true", help="Keep logs from last 7 days"
    )
    options_group.add_argument(
        "--validate",
        action="store_true",
        help="Validate installation state after cleaning",
    )

    return parser


def run(args: argparse.Namespace) -> int:
    """Run the clean command."""
    command = CleanCommand(args)
    return command.run()
