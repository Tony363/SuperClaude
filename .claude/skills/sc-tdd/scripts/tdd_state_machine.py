#!/usr/bin/env python3
"""TDD State Machine - Manages Red-Green-Refactor workflow state transitions.

This module tracks TDD workflow state, validates transitions, and persists state
to disk for recovery across Claude Code sessions.

State Machine:
    IDLE → RED_PENDING → RED_CONFIRMED → GREEN_PENDING →
    GREEN_CONFIRMED → REFACTOR_PENDING → REFACTOR_COMPLETE → [IDLE or next cycle]

Exit Codes:
    0 - State transition allowed
    2 - State transition blocked
    3 - Tooling error / cannot determine

NOTE: Uses `from __future__ import annotations` for Python 3.9 compatibility
with generic types (list[StateTransition]).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class TDDPhase(Enum):
    """TDD workflow phases."""
    IDLE = "IDLE"
    RED_PENDING = "RED_PENDING"
    RED_CONFIRMED = "RED_CONFIRMED"
    GREEN_PENDING = "GREEN_PENDING"
    GREEN_CONFIRMED = "GREEN_CONFIRMED"
    REFACTOR_PENDING = "REFACTOR_PENDING"
    REFACTOR_COMPLETE = "REFACTOR_COMPLETE"


@dataclass
class IntentTest:
    """Intent test information."""
    file: str
    name: Optional[str]  # Optional test name within file
    failure_type: Optional[str]  # e.g., "AssertionError", "semantic"
    excerpt_hash: Optional[str]  # Hash of failure message for verification


@dataclass
class StateTransition:
    """State transition record."""
    from_phase: str
    to_phase: str
    timestamp: str
    evidence: Optional[str] = None


@dataclass
class TDDState:
    """TDD workflow state."""
    scope_root: str
    current_phase: str
    framework: Optional[str] = None
    test_command: Optional[str] = None
    intent_test: Optional[IntentTest] = None
    transitions: list[StateTransition] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        if self.transitions is None:
            self.transitions = []
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()


class TDDStateMachine:
    """Manages TDD workflow state and transitions."""

    # Valid state transitions
    TRANSITIONS = {
        TDDPhase.IDLE: [TDDPhase.RED_PENDING],
        TDDPhase.RED_PENDING: [TDDPhase.RED_CONFIRMED, TDDPhase.IDLE],
        TDDPhase.RED_CONFIRMED: [TDDPhase.GREEN_PENDING],
        TDDPhase.GREEN_PENDING: [TDDPhase.GREEN_CONFIRMED, TDDPhase.RED_PENDING],
        TDDPhase.GREEN_CONFIRMED: [TDDPhase.REFACTOR_PENDING, TDDPhase.IDLE],
        TDDPhase.REFACTOR_PENDING: [TDDPhase.REFACTOR_COMPLETE, TDDPhase.GREEN_PENDING],
        TDDPhase.REFACTOR_COMPLETE: [TDDPhase.IDLE, TDDPhase.RED_PENDING],
    }

    def __init__(self, base_dir: Path = Path(".sc-tdd")):
        """Initialize state machine.

        Args:
            base_dir: Base directory for state storage
        """
        self.base_dir = Path(base_dir)
        self.state_dir = self.base_dir / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _scope_hash(self, scope_root: str) -> str:
        """Generate hash for scope root path.

        Args:
            scope_root: Absolute path to scope root

        Returns:
            Hex digest hash of scope root
        """
        return hashlib.sha256(scope_root.encode()).hexdigest()[:16]

    def _state_file(self, scope_root: str) -> Path:
        """Get state file path for scope.

        Args:
            scope_root: Absolute path to scope root

        Returns:
            Path to state JSON file
        """
        scope_hash = self._scope_hash(scope_root)
        scope_state_dir = self.state_dir / scope_hash
        scope_state_dir.mkdir(parents=True, exist_ok=True)
        return scope_state_dir / "state.json"

    def load_state(self, scope_root: str) -> Optional[TDDState]:
        """Load state for scope.

        Args:
            scope_root: Absolute path to scope root

        Returns:
            TDDState if exists, None otherwise
        """
        state_file = self._state_file(scope_root)
        if not state_file.exists():
            return None

        try:
            with open(state_file) as f:
                data = json.load(f)

            # Reconstruct dataclasses
            if data.get("intent_test"):
                data["intent_test"] = IntentTest(**data["intent_test"])

            if data.get("transitions"):
                data["transitions"] = [
                    StateTransition(**t) for t in data["transitions"]
                ]

            return TDDState(**data)
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            print(f"Error loading state: {e}", file=sys.stderr)
            return None

    def save_state(self, state: TDDState) -> bool:
        """Save state to disk.

        Args:
            state: TDDState to persist

        Returns:
            True if successful, False otherwise
        """
        state_file = self._state_file(state.scope_root)
        state.updated_at = datetime.utcnow().isoformat()

        try:
            # Convert dataclasses to dict
            state_dict = asdict(state)

            with open(state_file, "w") as f:
                json.dump(state_dict, f, indent=2)
            return True
        except (OSError, TypeError) as e:
            print(f"Error saving state: {e}", file=sys.stderr)
            return False

    def can_transition(self, from_phase: TDDPhase, to_phase: TDDPhase) -> bool:
        """Check if transition is valid.

        Args:
            from_phase: Current phase
            to_phase: Target phase

        Returns:
            True if transition allowed
        """
        return to_phase in self.TRANSITIONS.get(from_phase, [])

    def transition(
        self,
        state: TDDState,
        to_phase: TDDPhase,
        evidence: Optional[str] = None
    ) -> tuple[bool, str]:
        """Attempt state transition.

        Args:
            state: Current state
            to_phase: Target phase
            evidence: Evidence supporting transition

        Returns:
            (success: bool, message: str)
        """
        current = TDDPhase(state.current_phase)

        if not self.can_transition(current, to_phase):
            return False, f"Invalid transition: {current.value} → {to_phase.value}"

        # Record transition
        transition = StateTransition(
            from_phase=current.value,
            to_phase=to_phase.value,
            timestamp=datetime.utcnow().isoformat(),
            evidence=evidence
        )
        state.transitions.append(transition)
        state.current_phase = to_phase.value

        # Save state
        if not self.save_state(state):
            return False, "Failed to save state"

        return True, f"Transitioned: {current.value} → {to_phase.value}"

    def can_edit_production(self, phase: TDDPhase) -> bool:
        """Check if production code edits are allowed.

        Args:
            phase: Current phase

        Returns:
            True if production edits allowed
        """
        return phase in [
            TDDPhase.GREEN_PENDING,
            TDDPhase.REFACTOR_PENDING
        ]

    def can_edit_test(self, phase: TDDPhase, edit_type: str = "modify") -> bool:
        """Check if test edits are allowed.

        Args:
            phase: Current phase
            edit_type: Type of edit (modify, strengthen, weaken)

        Returns:
            True if test edits allowed
        """
        if phase == TDDPhase.RED_PENDING:
            return edit_type in ["modify", "strengthen"]
        if phase == TDDPhase.REFACTOR_PENDING:
            return edit_type in ["modify", "strengthen"]  # Cleanup only
        if phase == TDDPhase.GREEN_PENDING:
            return edit_type != "weaken"
        return False


def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="TDD State Machine")
    parser.add_argument("--scope-root", required=True, help="Scope root directory")
    parser.add_argument("--init", action="store_true", help="Initialize new state")
    parser.add_argument("--phase", help="Target phase for transition")
    parser.add_argument("--evidence", help="Evidence for transition")
    parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args()

    sm = TDDStateMachine()

    if args.init:
        # Initialize new state
        state = TDDState(
            scope_root=args.scope_root,
            current_phase=TDDPhase.IDLE.value
        )
        if sm.save_state(state):
            output = {
                "success": True,
                "phase": state.current_phase,
                "message": "State initialized"
            }
            print(json.dumps(output, indent=2) if args.json else output["message"])
            sys.exit(0)
        else:
            output = {"success": False, "error": "Failed to initialize state"}
            print(json.dumps(output, indent=2) if args.json else output["error"])
            sys.exit(3)

    # Load existing state
    state = sm.load_state(args.scope_root)
    if not state:
        output = {
            "success": False,
            "error": "No state found. Run with --init first."
        }
        print(json.dumps(output, indent=2) if args.json else output["error"])
        sys.exit(3)

    if args.phase:
        # Attempt transition
        try:
            to_phase = TDDPhase(args.phase)
            success, message = sm.transition(state, to_phase, args.evidence)

            output = {
                "success": success,
                "from_phase": state.transitions[-1].from_phase,
                "to_phase": state.current_phase,
                "message": message
            }

            print(json.dumps(output, indent=2) if args.json else message)
            sys.exit(0 if success else 2)
        except ValueError:
            output = {"success": False, "error": f"Invalid phase: {args.phase}"}
            print(json.dumps(output, indent=2) if args.json else output["error"])
            sys.exit(3)
    else:
        # Show current state
        output = {
            "success": True,
            "phase": state.current_phase,
            "scope_root": state.scope_root,
            "framework": state.framework,
            "intent_test": asdict(state.intent_test) if state.intent_test else None
        }
        print(json.dumps(output, indent=2))
        sys.exit(0)


if __name__ == "__main__":
    main()
