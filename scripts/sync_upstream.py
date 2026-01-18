#!/usr/bin/env python3
"""
Sync retro-metadata with RomM upstream changes.

This script helps track and synchronize changes between the RomM codebase
and the retro-metadata library.

Usage:
    python scripts/sync_upstream.py --romm-path /path/to/romm
    python scripts/sync_upstream.py --check-only  # Dry run
    python scripts/sync_upstream.py --generate-diff
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class FileChange:
    """Represents a change in a source file."""

    file_path: str
    change_type: str  # modified, added, deleted
    diff_lines: int = 0
    affected_modules: list[str] | None = None


def load_file_map(library_path: Path) -> dict[str, Any]:
    """Load the file mapping configuration.

    Args:
        library_path: Path to the library root

    Returns:
        File mapping configuration
    """
    map_path = library_path / "migration" / "file_map.yaml"
    if not map_path.exists():
        print(f"Error: File map not found at {map_path}")
        sys.exit(1)

    with open(map_path) as f:
        return yaml.safe_load(f)


def get_file_hash(file_path: Path) -> str:
    """Get MD5 hash of a file.

    Args:
        file_path: Path to the file

    Returns:
        MD5 hash string
    """
    if not file_path.exists():
        return ""

    with open(file_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def get_git_changes(romm_path: Path, since_commit: str | None = None) -> list[FileChange]:
    """Get changed files in RomM repository.

    Args:
        romm_path: Path to RomM repository
        since_commit: Optional commit to compare against

    Returns:
        List of file changes
    """
    changes = []

    # Get list of changed files
    cmd = ["git", "-C", str(romm_path), "status", "--porcelain"]
    if since_commit:
        cmd = ["git", "-C", str(romm_path), "diff", "--name-status", since_commit]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running git: {e}")
        return changes

    for line in result.stdout.strip().split("\n"):
        if not line:
            continue

        parts = line.split()
        if len(parts) >= 2:
            status = parts[0]
            file_path = parts[-1]

            # Map git status to change type
            if status.startswith("M"):
                change_type = "modified"
            elif status.startswith("A") or status == "??":
                change_type = "added"
            elif status.startswith("D"):
                change_type = "deleted"
            else:
                change_type = "unknown"

            changes.append(FileChange(
                file_path=file_path,
                change_type=change_type,
            ))

    return changes


def check_for_changes(
    romm_path: Path,
    library_path: Path,
    file_map: dict[str, Any],
) -> list[tuple[FileChange, list[str]]]:
    """Check for relevant changes in RomM.

    Args:
        romm_path: Path to RomM repository
        library_path: Path to library
        file_map: File mapping configuration

    Returns:
        List of (change, affected_modules) tuples
    """
    watch_patterns = file_map.get("watch_files", [])
    mappings = file_map.get("mappings", [])

    # Build source to target mapping
    source_to_targets: dict[str, list[str]] = {}
    for mapping in mappings:
        source = mapping["source"]
        targets = [t["module"] for t in mapping.get("targets", [])]
        source_to_targets[source] = targets

    # Get all changes
    changes = get_git_changes(romm_path)

    relevant_changes = []
    for change in changes:
        # Check if file matches watch patterns
        for pattern in watch_patterns:
            pattern_path = pattern.replace("*", "")
            if pattern_path in change.file_path:
                affected = source_to_targets.get(change.file_path, [])
                relevant_changes.append((change, affected))
                break

    return relevant_changes


def generate_diff_report(
    romm_path: Path,
    changes: list[tuple[FileChange, list[str]]],
) -> str:
    """Generate a markdown diff report.

    Args:
        romm_path: Path to RomM repository
        changes: List of changes with affected modules

    Returns:
        Markdown report string
    """
    report = "# RomM Upstream Changes Report\n\n"

    if not changes:
        report += "No relevant changes detected.\n"
        return report

    report += f"Found {len(changes)} relevant change(s):\n\n"

    for change, affected in changes:
        report += f"## {change.file_path}\n\n"
        report += f"- **Change Type**: {change.change_type}\n"

        if affected:
            report += f"- **Affected Modules**: {', '.join(affected)}\n"

        # Get diff
        try:
            result = subprocess.run(
                ["git", "-C", str(romm_path), "diff", "--stat", change.file_path],
                capture_output=True,
                text=True,
            )
            if result.stdout:
                report += f"\n```\n{result.stdout}\n```\n"
        except Exception:
            pass

        report += "\n"

    return report


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sync retro-metadata with RomM upstream changes"
    )
    parser.add_argument(
        "--romm-path",
        type=Path,
        default=Path.cwd().parent / "romm",
        help="Path to RomM repository",
    )
    parser.add_argument(
        "--library-path",
        type=Path,
        default=Path(__file__).parent.parent,
        help="Path to retro-metadata library",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check for changes, don't apply",
    )
    parser.add_argument(
        "--generate-diff",
        action="store_true",
        help="Generate a diff report",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file for diff report",
    )
    parser.add_argument(
        "--since",
        help="Git commit to compare against",
    )

    args = parser.parse_args()

    # Validate paths
    if not args.romm_path.exists():
        print(f"Error: RomM path not found: {args.romm_path}")
        sys.exit(1)

    if not args.library_path.exists():
        print(f"Error: Library path not found: {args.library_path}")
        sys.exit(1)

    # Load file map
    file_map = load_file_map(args.library_path)

    # Check for changes
    print(f"Checking for changes in {args.romm_path}...")
    changes = check_for_changes(args.romm_path, args.library_path, file_map)

    if not changes:
        print("No relevant changes detected.")
        return

    print(f"Found {len(changes)} relevant change(s):")
    for change, affected in changes:
        print(f"  - {change.file_path} ({change.change_type})")
        if affected:
            print(f"    Affects: {', '.join(affected)}")

    # Generate diff report
    if args.generate_diff:
        report = generate_diff_report(args.romm_path, changes)

        if args.output:
            args.output.write_text(report)
            print(f"\nReport written to {args.output}")
        else:
            print("\n" + report)

    # Check-only mode
    if args.check_only:
        print("\nCheck-only mode, no changes applied.")
        return

    # TODO: Implement automatic sync for safe changes
    print("\nManual review required for these changes.")
    print("Please update the affected modules in retro-metadata.")


if __name__ == "__main__":
    main()
