"""
Skill Persistence Layer for SuperClaude

Enables cross-session learning by:
1. Storing learned patterns from successful iterations
2. Extracting generalizable skills from execution results
3. Retrieving relevant skills for new tasks
4. Gating skill promotion through quality thresholds

Architecture:
    SkillStore (SQLite) ─> SkillExtractor ─> SkillRetriever
                              │
                              v
                       PromotionGate (PAL/tests)
                              │
                              v
                    .claude/skills/learned/

Compatible with Python 3.9+
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Thread-local storage for SQLite connections
_local = threading.local()


@dataclass
class LearnedSkill:
    """A skill extracted from successful execution patterns."""

    skill_id: str
    name: str
    description: str
    triggers: list[str]
    domain: str
    source_session: str
    source_repo: str
    learned_at: str
    patterns: list[str]  # Successful patterns/strategies
    anti_patterns: list[str]  # What to avoid
    quality_score: float
    iteration_count: int
    provenance: dict[str, Any]  # Full trace for auditability
    applicability_conditions: list[str]  # When this skill applies
    promoted: bool = False
    promotion_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LearnedSkill:
        return cls(**data)

    def to_skill_md(self) -> str:
        """Generate SKILL.md content for this learned skill."""
        triggers_str = ", ".join(self.triggers)
        patterns_str = "\n".join(f"- {p}" for p in self.patterns)
        anti_patterns_str = "\n".join(f"- {p}" for p in self.anti_patterns)
        conditions_str = "\n".join(f"- {c}" for c in self.applicability_conditions)

        return f"""---
name: {self.name}
description: {self.description}
learned: true
source_session: {self.source_session}
learned_at: {self.learned_at}
quality_score: {self.quality_score}
---

# {self.name.replace("-", " ").title()}

{self.description}

## Domain

{self.domain}

## Triggers

{triggers_str}

## Learned Patterns

These patterns were extracted from successful executions:

{patterns_str}

## Anti-Patterns

Avoid these approaches (they failed or caused issues):

{anti_patterns_str}

## Applicability Conditions

This skill applies when:

{conditions_str}

## Provenance

- **Source Session**: `{self.source_session}`
- **Source Repository**: `{self.source_repo}`
- **Learned At**: {self.learned_at}
- **Quality Score**: {self.quality_score}/100
- **Iterations**: {self.iteration_count}
- **Promoted**: {self.promoted} ({self.promotion_reason or "pending"})

## Integration

This is a **learned skill** automatically extracted from execution feedback.
It should be reviewed periodically and may be promoted to a permanent skill
after sufficient validation.
"""


@dataclass
class IterationFeedback:
    """Feedback from a single loop iteration."""

    session_id: str
    iteration: int
    quality_before: float
    quality_after: float
    improvements_applied: list[str]
    improvements_needed: list[str]
    changed_files: list[str]
    test_results: dict[str, Any]
    duration_seconds: float
    success: bool
    termination_reason: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IterationFeedback:
        return cls(**data)


class SkillStore:
    """
    SQLite-backed persistent storage for learned skills.

    Thread-safe with connection-per-thread pattern.
    """

    DEFAULT_DB_PATH = Path.home() / ".claude" / "learned_skills.db"

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection with WAL mode for concurrency."""
        if not hasattr(_local, "connection") or _local.connection is None:
            _local.connection = sqlite3.connect(
                str(self.db_path), check_same_thread=False, timeout=30.0
            )
            _local.connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrent access
            _local.connection.execute("PRAGMA journal_mode=WAL")
        return _local.connection

    def close(self) -> None:
        """Close the thread-local database connection."""
        if hasattr(_local, "connection") and _local.connection is not None:
            _local.connection.close()
            _local.connection = None

    def __enter__(self) -> "SkillStore":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _init_schema(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS learned_skills (
                skill_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                triggers TEXT,  -- JSON array
                domain TEXT,
                source_session TEXT,
                source_repo TEXT,
                learned_at TEXT,
                patterns TEXT,  -- JSON array
                anti_patterns TEXT,  -- JSON array
                quality_score REAL,
                iteration_count INTEGER,
                provenance TEXT,  -- JSON object
                applicability_conditions TEXT,  -- JSON array
                promoted INTEGER DEFAULT 0,
                promotion_reason TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS iteration_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                iteration INTEGER,
                quality_before REAL,
                quality_after REAL,
                improvements_applied TEXT,  -- JSON array
                improvements_needed TEXT,  -- JSON array
                changed_files TEXT,  -- JSON array
                test_results TEXT,  -- JSON object
                duration_seconds REAL,
                success INTEGER,
                termination_reason TEXT,
                timestamp TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS skill_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                applied_at TEXT,
                was_helpful INTEGER,  -- 1=yes, 0=no, NULL=unknown
                quality_impact REAL,  -- delta in quality score
                feedback TEXT,
                FOREIGN KEY (skill_id) REFERENCES learned_skills(skill_id)
            );

            CREATE INDEX IF NOT EXISTS idx_feedback_session
                ON iteration_feedback(session_id);
            CREATE INDEX IF NOT EXISTS idx_skills_domain
                ON learned_skills(domain);
            CREATE INDEX IF NOT EXISTS idx_skills_promoted
                ON learned_skills(promoted);
            CREATE INDEX IF NOT EXISTS idx_applications_skill
                ON skill_applications(skill_id);
        """)
        conn.commit()

    # --- Skill CRUD Operations ---

    def save_skill(self, skill: LearnedSkill) -> bool:
        """Save or update a learned skill. Returns True on success."""
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO learned_skills (
                    skill_id, name, description, triggers, domain,
                    source_session, source_repo, learned_at, patterns,
                    anti_patterns, quality_score, iteration_count,
                    provenance, applicability_conditions, promoted,
                    promotion_reason, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    skill.skill_id,
                    skill.name,
                    skill.description,
                    json.dumps(skill.triggers),
                    skill.domain,
                    skill.source_session,
                    skill.source_repo,
                    skill.learned_at,
                    json.dumps(skill.patterns),
                    json.dumps(skill.anti_patterns),
                    skill.quality_score,
                    skill.iteration_count,
                    json.dumps(skill.provenance),
                    json.dumps(skill.applicability_conditions),
                    1 if skill.promoted else 0,
                    skill.promotion_reason,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"[SkillStore] Failed to save skill {skill.skill_id}: {e}", file=sys.stderr)
            return False

    def get_skill(self, skill_id: str) -> Optional[LearnedSkill]:
        """Retrieve a skill by ID."""
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM learned_skills WHERE skill_id = ?", (skill_id,)
        ).fetchone()
        return self._row_to_skill(row) if row else None

    def get_promoted_skills(self) -> list[LearnedSkill]:
        """Get all promoted skills."""
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM learned_skills WHERE promoted = 1 ORDER BY quality_score DESC"
        ).fetchall()
        return [self._row_to_skill(row) for row in rows]

    def get_skills_by_domain(self, domain: str) -> list[LearnedSkill]:
        """Get skills matching a domain."""
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM learned_skills WHERE domain = ? ORDER BY quality_score DESC", (domain,)
        ).fetchall()
        return [self._row_to_skill(row) for row in rows]

    def search_skills(
        self,
        query: str,
        domain: Optional[str] = None,
        min_quality: float = 70.0,
        promoted_only: bool = False,
    ) -> List[LearnedSkill]:
        """Search skills by trigger keywords and filters."""
        conn = self._get_connection()

        sql = "SELECT * FROM learned_skills WHERE quality_score >= ?"
        params: list[Any] = [min_quality]

        if domain:
            sql += " AND domain = ?"
            params.append(domain)

        if promoted_only:
            sql += " AND promoted = 1"

        sql += " ORDER BY quality_score DESC"

        rows = conn.execute(sql, params).fetchall()

        # Filter by trigger match
        query_terms = set(query.lower().split())
        results = []
        for row in rows:
            skill = self._row_to_skill(row)
            skill_triggers = set(t.lower() for t in skill.triggers)
            if query_terms & skill_triggers:
                results.append(skill)

        return results

    def _row_to_skill(self, row: sqlite3.Row) -> LearnedSkill:
        """Convert database row to LearnedSkill object."""
        return LearnedSkill(
            skill_id=row["skill_id"],
            name=row["name"],
            description=row["description"] or "",
            triggers=json.loads(row["triggers"] or "[]"),
            domain=row["domain"] or "",
            source_session=row["source_session"] or "",
            source_repo=row["source_repo"] or "",
            learned_at=row["learned_at"] or "",
            patterns=json.loads(row["patterns"] or "[]"),
            anti_patterns=json.loads(row["anti_patterns"] or "[]"),
            quality_score=row["quality_score"] or 0.0,
            iteration_count=row["iteration_count"] or 0,
            provenance=json.loads(row["provenance"] or "{}"),
            applicability_conditions=json.loads(row["applicability_conditions"] or "[]"),
            promoted=bool(row["promoted"]),
            promotion_reason=row["promotion_reason"] or "",
        )

    # --- Iteration Feedback ---

    def save_feedback(self, feedback: IterationFeedback) -> bool:
        """Record iteration feedback for learning. Returns True on success."""
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO iteration_feedback (
                    session_id, iteration, quality_before, quality_after,
                    improvements_applied, improvements_needed, changed_files,
                    test_results, duration_seconds, success, termination_reason,
                    timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    feedback.session_id,
                    feedback.iteration,
                    feedback.quality_before,
                    feedback.quality_after,
                    json.dumps(feedback.improvements_applied),
                    json.dumps(feedback.improvements_needed),
                    json.dumps(feedback.changed_files),
                    json.dumps(feedback.test_results),
                    feedback.duration_seconds,
                    1 if feedback.success else 0,
                    feedback.termination_reason,
                    feedback.timestamp,
                ),
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(
                f"[SkillStore] Failed to save feedback for session {feedback.session_id}: {e}",
                file=sys.stderr,
            )
            return False

    def get_session_feedback(self, session_id: str) -> list[IterationFeedback]:
        """Get all feedback for a session."""
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM iteration_feedback WHERE session_id = ? ORDER BY iteration",
            (session_id,),
        ).fetchall()
        return [
            IterationFeedback(
                session_id=row["session_id"],
                iteration=row["iteration"],
                quality_before=row["quality_before"],
                quality_after=row["quality_after"],
                improvements_applied=json.loads(row["improvements_applied"] or "[]"),
                improvements_needed=json.loads(row["improvements_needed"] or "[]"),
                changed_files=json.loads(row["changed_files"] or "[]"),
                test_results=json.loads(row["test_results"] or "{}"),
                duration_seconds=row["duration_seconds"],
                success=bool(row["success"]),
                termination_reason=row["termination_reason"] or "",
                timestamp=row["timestamp"] or "",
            )
            for row in rows
        ]

    # --- Skill Application Tracking ---

    def record_skill_application(
        self,
        skill_id: str,
        session_id: str,
        was_helpful: Optional[bool] = None,
        quality_impact: Optional[float] = None,
        feedback: str = "",
    ) -> bool:
        """Record when a skill was applied and its effectiveness. Returns True on success."""
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO skill_applications (
                    skill_id, session_id, applied_at, was_helpful,
                    quality_impact, feedback
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    skill_id,
                    session_id,
                    datetime.now(timezone.utc).isoformat(),
                    1 if was_helpful else (0 if was_helpful is False else None),
                    quality_impact,
                    feedback,
                ),
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(
                f"[SkillStore] Failed to record application for skill {skill_id}: {e}",
                file=sys.stderr,
            )
            return False

    def get_skill_effectiveness(self, skill_id: str) -> Dict[str, Any]:
        """Calculate skill effectiveness metrics."""
        conn = self._get_connection()
        row = conn.execute(
            """
            SELECT
                COUNT(*) as applications,
                SUM(CASE WHEN was_helpful = 1 THEN 1 ELSE 0 END) as helpful_count,
                SUM(CASE WHEN was_helpful = 0 THEN 1 ELSE 0 END) as unhelpful_count,
                AVG(quality_impact) as avg_quality_impact
            FROM skill_applications
            WHERE skill_id = ?
        """,
            (skill_id,),
        ).fetchone()

        return {
            "applications": row["applications"] or 0,
            "helpful_count": row["helpful_count"] or 0,
            "unhelpful_count": row["unhelpful_count"] or 0,
            "success_rate": (
                (row["helpful_count"] or 0) / row["applications"] if row["applications"] else 0
            ),
            "avg_quality_impact": row["avg_quality_impact"] or 0.0,
        }

    def get_bulk_skill_effectiveness(self, skill_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Calculate skill effectiveness metrics for multiple skills in one query.

        Returns a dict mapping skill_id -> effectiveness metrics.
        This avoids N+1 queries when scoring multiple skills.
        """
        if not skill_ids:
            return {}

        conn = self._get_connection()
        placeholders = ",".join("?" for _ in skill_ids)
        rows = conn.execute(  # nosec B608
            f"""
            SELECT
                skill_id,
                COUNT(*) as applications,
                SUM(CASE WHEN was_helpful = 1 THEN 1 ELSE 0 END) as helpful_count,
                SUM(CASE WHEN was_helpful = 0 THEN 1 ELSE 0 END) as unhelpful_count,
                AVG(quality_impact) as avg_quality_impact
            FROM skill_applications
            WHERE skill_id IN ({placeholders})
            GROUP BY skill_id
        """,
            skill_ids,
        ).fetchall()

        results: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            apps = row["applications"] or 0
            helpful = row["helpful_count"] or 0
            results[row["skill_id"]] = {
                "applications": apps,
                "helpful_count": helpful,
                "unhelpful_count": row["unhelpful_count"] or 0,
                "success_rate": helpful / apps if apps else 0,
                "avg_quality_impact": row["avg_quality_impact"] or 0.0,
            }

        # Fill in missing skill_ids with default values
        for skill_id in skill_ids:
            if skill_id not in results:
                results[skill_id] = {
                    "applications": 0,
                    "helpful_count": 0,
                    "unhelpful_count": 0,
                    "success_rate": 0,
                    "avg_quality_impact": 0.0,
                }

        return results


class SkillExtractor:
    """
    Extracts generalizable skills from iteration feedback.

    Analyzes patterns across iterations to identify:
    - Successful strategies that led to quality improvements
    - Anti-patterns that caused regressions or stalls
    - Conditions under which patterns apply
    """

    def __init__(self, store: SkillStore):
        self.store = store

    def extract_from_session(
        self, session_id: str, repo_path: str = "", domain: str = "general"
    ) -> Optional[LearnedSkill]:
        """
        Extract a learned skill from a completed session.

        Returns None if the session doesn't have enough signal
        or didn't achieve quality threshold.
        """
        feedback_list = self.store.get_session_feedback(session_id)

        if not feedback_list:
            return None

        # Only extract from successful sessions
        final_feedback = feedback_list[-1]
        if not final_feedback.success or final_feedback.quality_after < 70.0:
            return None

        # Need at least 2 iterations to learn from
        if len(feedback_list) < 2:
            return None

        # Extract patterns
        patterns = self._extract_patterns(feedback_list)
        anti_patterns = self._extract_anti_patterns(feedback_list)
        triggers = self._extract_triggers(feedback_list)
        conditions = self._extract_conditions(feedback_list)

        # Generate skill ID and name
        skill_id = self._generate_skill_id(session_id, patterns)
        name = self._generate_skill_name(patterns, domain)

        return LearnedSkill(
            skill_id=skill_id,
            name=name,
            description=f"Learned skill extracted from session {session_id[:8]}",
            triggers=triggers,
            domain=domain,
            source_session=session_id,
            source_repo=repo_path,
            learned_at=datetime.now(timezone.utc).isoformat(),
            patterns=patterns,
            anti_patterns=anti_patterns,
            quality_score=final_feedback.quality_after,
            iteration_count=len(feedback_list),
            provenance={
                "session_id": session_id,
                "repo_path": repo_path,
                "iterations": len(feedback_list),
                "quality_progression": [
                    {"iteration": f.iteration, "before": f.quality_before, "after": f.quality_after}
                    for f in feedback_list
                ],
                "total_duration": sum(f.duration_seconds for f in feedback_list),
                "termination_reason": final_feedback.termination_reason,
            },
            applicability_conditions=conditions,
            promoted=False,
            promotion_reason="",
        )

    def _extract_patterns(self, feedback_list: list[IterationFeedback]) -> list[str]:
        """Extract successful improvement patterns."""
        patterns = []

        for i, feedback in enumerate(feedback_list):
            # Quality improved this iteration
            if feedback.quality_after > feedback.quality_before:
                for improvement in feedback.improvements_applied:
                    patterns.append(f"[Iter {feedback.iteration}] {improvement}")

        # Deduplicate while preserving order
        seen = set()
        unique_patterns = []
        for p in patterns:
            # Normalize for dedup
            normalized = p.split("] ", 1)[-1].lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                unique_patterns.append(p)

        return unique_patterns[:10]  # Limit to top 10 patterns

    def _extract_anti_patterns(self, feedback_list: list[IterationFeedback]) -> list[str]:
        """Extract patterns that didn't work or caused issues."""
        anti_patterns = []

        for feedback in feedback_list:
            # Quality decreased or stalled
            if feedback.quality_after <= feedback.quality_before:
                for improvement in feedback.improvements_applied:
                    anti_patterns.append(f"[Failed] {improvement}")

            # Improvements still needed at end
            if not feedback.success:
                for needed in feedback.improvements_needed:
                    anti_patterns.append(f"[Unresolved] {needed}")

        return anti_patterns[:5]  # Limit to top 5 anti-patterns

    def _extract_triggers(self, feedback_list: list[IterationFeedback]) -> list[str]:
        """Extract trigger keywords from changed files and improvements."""
        triggers = set()

        for feedback in feedback_list:
            # Extract from file paths
            for file_path in feedback.changed_files:
                parts = Path(file_path).parts
                for part in parts:
                    if part not in {"src", "lib", "test", "tests", "spec", "."}:
                        triggers.add(part.lower())

                # Extract extension
                ext = Path(file_path).suffix.lstrip(".")
                if ext:
                    triggers.add(ext)

            # Extract from improvements
            for improvement in feedback.improvements_applied:
                words = improvement.lower().split()
                for word in words:
                    if len(word) > 3 and word.isalpha():
                        triggers.add(word)

        # Filter common words
        stopwords = {"the", "and", "for", "with", "from", "this", "that", "have", "been"}
        triggers = triggers - stopwords

        return sorted(triggers)[:15]  # Limit to 15 triggers

    def _extract_conditions(self, feedback_list: list[IterationFeedback]) -> list[str]:
        """Extract applicability conditions."""
        conditions = []

        # Analyze file types
        extensions = set()
        for feedback in feedback_list:
            for file_path in feedback.changed_files:
                ext = Path(file_path).suffix
                if ext:
                    extensions.add(ext)

        if extensions:
            conditions.append(f"File types: {', '.join(sorted(extensions))}")

        # Analyze test presence
        had_tests = any(feedback.test_results.get("ran", False) for feedback in feedback_list)
        if had_tests:
            conditions.append("Project has test suite")

        # Analyze iteration count
        if len(feedback_list) >= 3:
            conditions.append("Complex task requiring multiple iterations")

        return conditions

    def _generate_skill_id(self, session_id: str, patterns: list[str]) -> str:
        """Generate unique skill ID."""
        content = f"{session_id}:{':'.join(patterns)}"
        return f"learned-{hashlib.sha256(content.encode()).hexdigest()[:12]}"

    def _generate_skill_name(self, patterns: list[str], domain: str) -> str:
        """Generate human-readable skill name."""
        if not patterns:
            return f"learned-{domain}-skill"

        # Extract key words from first pattern
        first_pattern = patterns[0].split("] ", 1)[-1] if patterns else ""
        words = [w for w in first_pattern.split()[:3] if len(w) > 2]
        name_part = "-".join(words).lower() if words else "general"

        return f"learned-{domain}-{name_part}"


class SkillRetriever:
    """
    Retrieves relevant learned skills for a given task context.

    Uses trigger matching and domain filtering to find applicable skills.
    """

    def __init__(self, store: SkillStore):
        self.store = store

    def retrieve(
        self,
        task_description: str,
        file_paths: Optional[List[str]] = None,
        domain: Optional[str] = None,
        max_skills: int = 3,
        promoted_only: bool = True,
    ) -> List[Tuple[LearnedSkill, float]]:
        """
        Retrieve relevant skills for a task.

        Returns list of (skill, relevance_score) tuples.
        """
        # Extract search terms from task
        search_terms = self._extract_search_terms(task_description, file_paths)

        # Get candidate skills
        candidates = self.store.search_skills(
            query=" ".join(search_terms),
            domain=domain,
            min_quality=50.0,
            promoted_only=promoted_only,
        )

        if not candidates:
            return []

        # Batch fetch effectiveness data to avoid N+1 queries
        skill_ids = [s.skill_id for s in candidates]
        effectiveness_map = self.store.get_bulk_skill_effectiveness(skill_ids)

        # Score and rank using pre-fetched effectiveness
        scored = []
        for skill in candidates:
            effectiveness = effectiveness_map.get(skill.skill_id, {})
            score = self._score_relevance(skill, search_terms, file_paths, effectiveness)
            if score > 0:
                scored.append((skill, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored[:max_skills]

    def _extract_search_terms(self, task_description: str, file_paths: Optional[List[str]]) -> set:
        """Extract search terms from task context."""
        terms = set()

        # From task description
        words = task_description.lower().split()
        for word in words:
            if len(word) > 3 and word.isalpha():
                terms.add(word)

        # From file paths
        if file_paths:
            for path in file_paths:
                parts = Path(path).parts
                for part in parts:
                    if part not in {"src", "lib", "test", "."}:
                        terms.add(part.lower())

                ext = Path(path).suffix.lstrip(".")
                if ext:
                    terms.add(ext)

        return terms

    def _score_relevance(
        self,
        skill: LearnedSkill,
        search_terms: set,
        file_paths: Optional[List[str]],
        effectiveness: Optional[Dict[str, Any]] = None,
    ) -> float:
        """Score skill relevance to current context."""
        score = 0.0

        # Trigger match (40%)
        skill_triggers = set(t.lower() for t in skill.triggers)
        trigger_overlap = len(search_terms & skill_triggers)
        if skill_triggers:
            score += 0.4 * (trigger_overlap / len(skill_triggers))

        # Quality score (30%)
        score += 0.3 * (skill.quality_score / 100.0)

        # Promoted bonus (20%)
        if skill.promoted:
            score += 0.2

        # Effectiveness history (10%) - use pre-fetched data if available
        if effectiveness is None:
            effectiveness = self.store.get_skill_effectiveness(skill.skill_id)
        if effectiveness.get("applications", 0) > 0:
            score += 0.1 * effectiveness.get("success_rate", 0)

        return score


class PromotionGate:
    """
    Gates skill promotion based on quality thresholds and validation.

    Skills must pass validation before being promoted to permanent status.
    """

    # Promotion thresholds
    MIN_QUALITY_SCORE = 85.0
    MIN_APPLICATIONS = 2
    MIN_SUCCESS_RATE = 0.7

    def __init__(self, store: SkillStore, skills_dir: Optional[Path] = None):
        self.store = store
        self.skills_dir = skills_dir or (Path.home() / ".claude" / "skills" / "learned")

    def evaluate(self, skill: LearnedSkill) -> Tuple[bool, str]:
        """
        Evaluate if a skill should be promoted.

        Returns (should_promote, reason).
        """
        reasons = []

        # Check quality score
        if skill.quality_score < self.MIN_QUALITY_SCORE:
            reasons.append(
                f"Quality score {skill.quality_score:.1f} below threshold {self.MIN_QUALITY_SCORE}"
            )

        # Check application history
        effectiveness = self.store.get_skill_effectiveness(skill.skill_id)

        if effectiveness["applications"] < self.MIN_APPLICATIONS:
            reasons.append(
                f"Only {effectiveness['applications']} applications, need {self.MIN_APPLICATIONS}"
            )
        elif effectiveness["success_rate"] < self.MIN_SUCCESS_RATE:
            reasons.append(
                f"Success rate {effectiveness['success_rate']:.1%} below {self.MIN_SUCCESS_RATE:.0%}"
            )

        if reasons:
            return False, "; ".join(reasons)

        return True, "Meets all promotion criteria"

    def promote(self, skill: LearnedSkill, reason: str = "") -> Optional[Path]:
        """
        Promote a skill to permanent status.

        Creates SKILL.md in the learned skills directory.
        Returns the path to the created skill, or None on failure.

        Uses skill_id for directory name to prevent path traversal attacks.
        Promotion is atomic: if file write fails, DB change is rolled back.
        """
        # Evaluate first
        should_promote, eval_reason = self.evaluate(skill)

        if not should_promote:
            return None

        # Store original state for rollback
        original_promoted = skill.promoted
        original_reason = skill.promotion_reason

        # Update skill status
        skill.promoted = True
        skill.promotion_reason = reason or eval_reason

        # Use skill_id for directory name (safe hash, no path traversal risk)
        # Keep skill.name in SKILL.md content for human readability
        skill_dir = self.skills_dir / skill.skill_id
        skill_md_path = skill_dir / "SKILL.md"
        metadata_path = skill_dir / "metadata.json"

        try:
            # Create skill directory and files
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_md_path.write_text(skill.to_skill_md())
            metadata_path.write_text(json.dumps(skill.to_dict(), indent=2))

            # Save to database only after files are successfully written
            if not self.store.save_skill(skill):
                # DB save failed, rollback files
                raise IOError("Database save failed")

            return skill_md_path

        except (IOError, OSError) as e:
            # Rollback skill state
            skill.promoted = original_promoted
            skill.promotion_reason = original_reason

            # Clean up any partially created files
            try:
                if metadata_path.exists():
                    metadata_path.unlink()
                if skill_md_path.exists():
                    skill_md_path.unlink()
                if skill_dir.exists() and not any(skill_dir.iterdir()):
                    skill_dir.rmdir()
            except OSError:
                pass  # Best effort cleanup

            print(f"[PromotionGate] Failed to promote skill {skill.skill_id}: {e}", file=sys.stderr)
            return None

    def list_pending(self) -> List[LearnedSkill]:
        """List skills pending promotion review."""
        conn = self.store._get_connection()
        rows = conn.execute(
            """
            SELECT * FROM learned_skills
            WHERE promoted = 0 AND quality_score >= ?
            ORDER BY quality_score DESC
        """,
            (self.MIN_QUALITY_SCORE - 10,),
        ).fetchall()

        return [self.store._row_to_skill(row) for row in rows]


# --- Convenience Functions ---


def get_default_store() -> SkillStore:
    """Get the default skill store instance."""
    return SkillStore()


def learn_from_session(
    session_id: str, repo_path: str = "", domain: str = "general", auto_promote: bool = False
) -> Optional[LearnedSkill]:
    """
    Convenience function to extract and optionally promote a skill from a session.

    Usage:
        from core.skill_persistence import learn_from_session

        skill = learn_from_session(
            session_id="abc123",
            repo_path="/path/to/repo",
            domain="backend",
            auto_promote=True
        )
    """
    store = get_default_store()
    extractor = SkillExtractor(store)

    skill = extractor.extract_from_session(session_id, repo_path, domain)

    if skill is None:
        return None

    store.save_skill(skill)

    if auto_promote:
        gate = PromotionGate(store)
        gate.promote(skill)

    return skill


def retrieve_skills_for_task(
    task_description: str, file_paths: Optional[List[str]] = None, domain: Optional[str] = None
) -> List[LearnedSkill]:
    """
    Convenience function to retrieve relevant skills for a task.

    Usage:
        from core.skill_persistence import retrieve_skills_for_task

        skills = retrieve_skills_for_task(
            task_description="Implement user authentication",
            file_paths=["src/auth/login.py"],
            domain="backend"
        )
    """
    store = get_default_store()
    retriever = SkillRetriever(store)

    results = retriever.retrieve(
        task_description=task_description,
        file_paths=file_paths,
        domain=domain,
        promoted_only=False,  # Include non-promoted for now
    )

    return [skill for skill, _score in results]
